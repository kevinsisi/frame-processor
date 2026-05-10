"""NAFNet 影像降噪。

模型：NAFNet-SIDD-width32（小型 SIDD 預訓練版本，~17M params，CPU 可用）。
參考論文：Chen et al. "Simple Baselines for Image Restoration" (ECCV 2022).

策略：
- PyTorch 直接定義 NAFNet 架構（不依賴 basicsr，避免 BasicSR 巨型相依）
- 權重 lazy download：第一次呼叫時從官方 Google Drive 權重下載到 NAFNET_DIR
- CPU 推理：對 > tile 的圖切 tile（預設 512x512 with 32px overlap），最後拼回去
- GPU：``torch.cuda.is_available()`` 自動偵測
- 強度（DenoiseStrength）：light/medium/heavy 先產生降噪候選圖，再用 edge-aware
  blend 合回原圖。平坦區域強力清噪；建築線條、窗框、車身邊緣保留更多亮度細節。
- medium/heavy 會把 NAFNet 與 OpenCV 經典降噪混合，避免 NAFNet 對極端高 ISO /
  彩色顆粒太保守而看起來沒效果，但不再對 NAFNet 結果做第二次全量平滑。

公開介面：``denoise(image: PIL.Image, strength: DenoiseStrength) -> PIL.Image``
"""

from __future__ import annotations

import logging
import os
import shutil
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image

from api.config import settings
from models.enums import DenoiseStrength

logger = logging.getLogger(__name__)

NAFNET_GOOGLE_DRIVE_FILE_ID = "1lsByk21Xw-6aW7epCwOQxvm6HYCQZPHZ"
NAFNET_GOOGLE_DRIVE_DOWNLOAD_URL = (
    "https://drive.usercontent.google.com/download?"
    f"id={NAFNET_GOOGLE_DRIVE_FILE_ID}&export=download&confirm=t"
)
NAFNET_WEIGHTS_URL = os.environ.get(
    "NAFNET_WEIGHTS_URL",
    NAFNET_GOOGLE_DRIVE_DOWNLOAD_URL,
)
NAFNET_WEIGHTS_FILENAME = "NAFNet-SIDD-width32.pth"

STRENGTH_BLEND: dict[DenoiseStrength, float] = {
    DenoiseStrength.NONE: 0.0,
    DenoiseStrength.LIGHT: 0.35,
    DenoiseStrength.MEDIUM: 0.8,
    DenoiseStrength.HEAVY: 0.8,
}

CLASSICAL_POST_BLEND: dict[DenoiseStrength, float] = {
    DenoiseStrength.NONE: 0.0,
    DenoiseStrength.LIGHT: 0.0,
    DenoiseStrength.MEDIUM: 0.65,
    DenoiseStrength.HEAVY: 0.6,
}

DETAIL_PROTECTION: dict[DenoiseStrength, float] = {
    DenoiseStrength.NONE: 0.0,
    DenoiseStrength.LIGHT: 0.25,
    DenoiseStrength.MEDIUM: 0.55,
    DenoiseStrength.HEAVY: 0.72,
}

CHROMA_EXTRA_BLEND: dict[DenoiseStrength, float] = {
    DenoiseStrength.NONE: 0.0,
    DenoiseStrength.LIGHT: 0.1,
    DenoiseStrength.MEDIUM: 0.18,
    DenoiseStrength.HEAVY: 0.1,
}

DETAIL_STRUCTURE_BLUR_SIGMA = 1.8
DETAIL_CANNY_LOW = 55
DETAIL_CANNY_HIGH = 140
DETAIL_EDGE_BLUR_SIGMA = 1.6
DETAIL_LOCAL_WINDOW = 7
DETAIL_LOCAL_STD_FLOOR = 0.08
DETAIL_LOCAL_STD_RANGE = 0.16

_model = None
_device = None
_model_lock = Lock()


class DenoiseError(RuntimeError):
    pass


def denoise(image: Image.Image, strength: DenoiseStrength) -> Image.Image:
    if strength is DenoiseStrength.NONE:
        return image
    rgb = np.array(image.convert("RGB"), dtype=np.float32) / 255.0
    try:
        denoised = _run_nafnet(rgb)
        post_alpha = CLASSICAL_POST_BLEND[strength]
        if post_alpha:
            classical = _run_opencv_denoise(rgb, strength)
            denoised = post_alpha * classical + (1.0 - post_alpha) * denoised
    except DenoiseError as exc:
        logger.warning(
            "NAFNet unavailable; using quality-preserving OpenCV fallback: %s",
            exc,
        )
        denoised = _run_opencv_denoise(rgb, strength)
    blended = _blend_preserving_detail(rgb, denoised, strength)
    blended = np.clip(blended * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(blended)


def _run_opencv_denoise(rgb: np.ndarray, strength: DenoiseStrength) -> np.ndarray:
    """Fallback when NAFNet weights are unavailable in the deploy environment."""

    import cv2

    h_value = {
        DenoiseStrength.LIGHT: 6,
        DenoiseStrength.MEDIUM: 20,
        DenoiseStrength.HEAVY: 20,
    }.get(strength, 0)
    if h_value <= 0:
        return rgb
    image_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(image_u8, cv2.COLOR_RGB2BGR)
    denoised = cv2.fastNlMeansDenoisingColored(
        bgr,
        None,
        h=h_value,
        hColor=max(int(h_value * 1.2), 4),
        templateWindowSize=7,
        searchWindowSize=25 if strength is DenoiseStrength.HEAVY else 21,
    )
    return cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def _blend_preserving_detail(
    original: np.ndarray,
    denoised: np.ndarray,
    strength: DenoiseStrength,
) -> np.ndarray:
    import cv2

    base_alpha = STRENGTH_BLEND[strength]
    if base_alpha <= 0:
        return original

    detail_mask = _detail_protection_mask(original)
    protection = DETAIL_PROTECTION[strength]
    luma_alpha = np.clip(base_alpha * (1.0 - protection * detail_mask), 0.0, 1.0)
    chroma_alpha = np.clip(
        min(base_alpha + CHROMA_EXTRA_BLEND[strength], 1.0)
        * (1.0 - protection * 0.2 * detail_mask),
        0.0,
        1.0,
    )

    original_ycc = cv2.cvtColor(original.astype(np.float32), cv2.COLOR_RGB2YCrCb)
    denoised_ycc = cv2.cvtColor(denoised.astype(np.float32), cv2.COLOR_RGB2YCrCb)
    blended_ycc = original_ycc.copy()
    blended_ycc[..., :1] = (
        luma_alpha * denoised_ycc[..., :1] + (1.0 - luma_alpha) * original_ycc[..., :1]
    )
    blended_ycc[..., 1:] = (
        chroma_alpha * denoised_ycc[..., 1:] + (1.0 - chroma_alpha) * original_ycc[..., 1:]
    )
    return np.clip(cv2.cvtColor(blended_ycc, cv2.COLOR_YCrCb2RGB), 0.0, 1.0)


def _detail_protection_mask(rgb: np.ndarray) -> np.ndarray:
    import cv2

    rgb_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY)
    structure = cv2.GaussianBlur(gray, (0, 0), DETAIL_STRUCTURE_BLUR_SIGMA)

    edges = cv2.Canny(structure, DETAIL_CANNY_LOW, DETAIL_CANNY_HIGH)
    edges = cv2.dilate(edges, np.ones((3, 3), dtype=np.uint8), iterations=1)
    edge_mask = cv2.GaussianBlur(
        edges.astype(np.float32) / 255.0,
        (0, 0),
        DETAIL_EDGE_BLUR_SIGMA,
    )

    structure_f = structure.astype(np.float32) / 255.0
    local_mean = cv2.blur(structure_f, (DETAIL_LOCAL_WINDOW, DETAIL_LOCAL_WINDOW))
    local_mean_sq = cv2.blur(
        structure_f * structure_f,
        (DETAIL_LOCAL_WINDOW, DETAIL_LOCAL_WINDOW),
    )
    local_std = np.sqrt(np.maximum(local_mean_sq - local_mean * local_mean, 0.0))
    texture_mask = np.clip(
        (local_std - DETAIL_LOCAL_STD_FLOOR) / DETAIL_LOCAL_STD_RANGE,
        0.0,
        1.0,
    )

    detail_mask = np.maximum(edge_mask, texture_mask)
    detail_mask = cv2.GaussianBlur(detail_mask, (0, 0), 0.8)
    return np.clip(detail_mask[..., np.newaxis], 0.0, 1.0)


def _run_nafnet(rgb: np.ndarray) -> np.ndarray:
    import torch  # noqa: F401

    model, device = _ensure_model()
    h, w, _ = rgb.shape
    tile = max(int(settings.nafnet_tile_size), 128)
    if h <= tile and w <= tile:
        return _infer_tile(model, device, rgb)

    overlap = 32
    output = np.zeros_like(rgb)
    weight = np.zeros((h, w, 1), dtype=np.float32)
    for y in range(0, h, tile - overlap):
        for x in range(0, w, tile - overlap):
            y2 = min(y + tile, h)
            x2 = min(x + tile, w)
            y1 = max(0, y2 - tile)
            x1 = max(0, x2 - tile)
            patch = rgb[y1:y2, x1:x2]
            denoised_patch = _infer_tile(model, device, patch)
            output[y1:y2, x1:x2] += denoised_patch
            weight[y1:y2, x1:x2] += 1.0
    return output / np.maximum(weight, 1e-6)


def _infer_tile(model, device, rgb: np.ndarray) -> np.ndarray:
    import torch

    h, w, _ = rgb.shape
    pad_h = (8 - h % 8) % 8
    pad_w = (8 - w % 8) % 8
    if pad_h or pad_w:
        rgb = np.pad(rgb, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect")
    tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(tensor)
    arr = out.squeeze(0).clamp(0, 1).cpu().numpy().transpose(1, 2, 0)
    return arr[:h, :w, :]


def _ensure_model():
    global _model, _device
    with _model_lock:
        if _model is not None:
            return _model, _device
        import torch

        weights_path = _download_weights()
        device_str = "cuda" if torch.cuda.is_available() else "cpu"
        device = torch.device(device_str)
        net_cls = __getattr__("NAFNet")
        net = net_cls(
            width=32,
            enc_blk_nums=(2, 2, 4, 8),
            middle_blk_num=12,
            dec_blk_nums=(2, 2, 2, 2),
        )
        state = torch.load(weights_path, map_location=device)
        if isinstance(state, dict) and "params" in state:
            state = state["params"]
        net.load_state_dict(state, strict=False)
        net.eval()
        net.to(device)
        _model = net
        _device = device
        return _model, _device


def _download_weights() -> Path:
    weights_dir = Path(settings.nafnet_dir)
    weights_dir.mkdir(parents=True, exist_ok=True)
    target = weights_dir / NAFNET_WEIGHTS_FILENAME
    if target.exists() and target.stat().st_size > 1_000_000:
        return target
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        _download_weight_file(NAFNET_WEIGHTS_URL, tmp)
        tmp.replace(target)
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise DenoiseError(
            f"failed to download NAFNet weights from {NAFNET_WEIGHTS_URL}: {exc}"
        ) from exc
    return target


def _download_weight_file(url: str, target: Path) -> None:
    if "drive.google.com" in url or "drive.usercontent.google.com" in url:
        _download_google_drive_file(url, target)
        return
    with urllib.request.urlopen(url, timeout=120) as resp, target.open("wb") as out:
        shutil.copyfileobj(resp, out)


def _download_google_drive_file(url: str, target: Path) -> None:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    with opener.open(url, timeout=120) as resp:
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            with target.open("wb") as out:
                shutil.copyfileobj(resp, out)
            return
        html = resp.read().decode("utf-8", errors="replace")
    params = _google_drive_confirm_params(html)
    if not params:
        raise DenoiseError(
            "Google Drive did not return a downloadable NAFNet confirmation form"
        )
    confirm_url = "https://drive.usercontent.google.com/download?" + urllib.parse.urlencode(params)
    with opener.open(confirm_url, timeout=120) as resp:
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" in content_type:
            raise DenoiseError("Google Drive returned HTML instead of NAFNet weights")
        with target.open("wb") as out:
            shutil.copyfileobj(resp, out)


def _google_drive_confirm_params(html: str) -> dict[str, str]:
    parser = _GoogleDriveConfirmParser()
    parser.feed(html)
    if "confirm" not in parser.fields:
        return {}
    return {
        key: parser.fields[key]
        for key in ("id", "export", "confirm", "uuid")
        if key in parser.fields
    }


class _GoogleDriveConfirmParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        if values.get("type") != "hidden":
            return
        name = values.get("name")
        if name:
            self.fields[name] = values.get("value") or ""


# ---------------------------------------------------------------------------
# NAFNet architecture (Chen et al., ECCV 2022) — minimal inline reimplementation.
# Lazy-imported via __getattr__ so importing this module doesn't require torch.
# ---------------------------------------------------------------------------


def _build_nafnet_class():
    import torch
    import torch.nn as nn

    class LayerNorm2d(nn.Module):
        def __init__(self, channels, eps=1e-6):
            super().__init__()
            self.weight = nn.Parameter(torch.ones(channels))
            self.bias = nn.Parameter(torch.zeros(channels))
            self.eps = eps

        def forward(self, x):
            mu = x.mean(1, keepdim=True)
            var = (x - mu).pow(2).mean(1, keepdim=True)
            x = (x - mu) / (var + self.eps).sqrt()
            return x * self.weight.view(1, -1, 1, 1) + self.bias.view(1, -1, 1, 1)

    class SimpleGate(nn.Module):
        def forward(self, x):
            x1, x2 = x.chunk(2, dim=1)
            return x1 * x2

    class NAFBlock(nn.Module):
        def __init__(self, c, dw_expand=2, ffn_expand=2):
            super().__init__()
            dw_channel = c * dw_expand
            ffn_channel = c * ffn_expand
            self.conv1 = nn.Conv2d(c, dw_channel, 1)
            self.conv2 = nn.Conv2d(
                dw_channel, dw_channel, 3, padding=1, groups=dw_channel
            )
            self.conv3 = nn.Conv2d(dw_channel // 2, c, 1)
            self.sca = nn.Sequential(
                nn.AdaptiveAvgPool2d(1),
                nn.Conv2d(dw_channel // 2, dw_channel // 2, 1),
            )
            self.norm1 = LayerNorm2d(c)
            self.norm2 = LayerNorm2d(c)
            self.conv4 = nn.Conv2d(c, ffn_channel, 1)
            self.conv5 = nn.Conv2d(ffn_channel // 2, c, 1)
            self.sg = SimpleGate()
            self.beta = nn.Parameter(torch.zeros(1, c, 1, 1))
            self.gamma = nn.Parameter(torch.zeros(1, c, 1, 1))

        def forward(self, inp):
            x = self.norm1(inp)
            x = self.conv1(x)
            x = self.conv2(x)
            x = self.sg(x)
            x = x * self.sca(x)
            x = self.conv3(x)
            y = inp + x * self.beta
            x = self.norm2(y)
            x = self.conv4(x)
            x = self.sg(x)
            x = self.conv5(x)
            return y + x * self.gamma

    class NAFNetImpl(nn.Module):
        def __init__(
            self,
            img_channel=3,
            width=32,
            middle_blk_num=12,
            enc_blk_nums=(2, 2, 4, 8),
            dec_blk_nums=(2, 2, 2, 2),
        ):
            super().__init__()
            self.intro = nn.Conv2d(img_channel, width, 3, padding=1)
            self.ending = nn.Conv2d(width, img_channel, 3, padding=1)
            self.encoders = nn.ModuleList()
            self.decoders = nn.ModuleList()
            self.downs = nn.ModuleList()
            self.ups = nn.ModuleList()
            chan = width
            for n in enc_blk_nums:
                self.encoders.append(nn.Sequential(*[NAFBlock(chan) for _ in range(n)]))
                self.downs.append(nn.Conv2d(chan, 2 * chan, 2, 2))
                chan *= 2
            self.middle_blks = nn.Sequential(
                *[NAFBlock(chan) for _ in range(middle_blk_num)]
            )
            for n in dec_blk_nums:
                self.ups.append(
                    nn.Sequential(
                        nn.Conv2d(chan, chan * 2, 1, bias=False),
                        nn.PixelShuffle(2),
                    )
                )
                chan //= 2
                self.decoders.append(
                    nn.Sequential(*[NAFBlock(chan) for _ in range(n)])
                )

        def forward(self, x):
            x_in = x
            x = self.intro(x)
            encs = []
            for enc, down in zip(self.encoders, self.downs, strict=True):
                x = enc(x)
                encs.append(x)
                x = down(x)
            x = self.middle_blks(x)
            for dec, up, enc_skip in zip(
                self.decoders, self.ups, encs[::-1], strict=True
            ):
                x = up(x)
                x = x + enc_skip
                x = dec(x)
            x = self.ending(x)
            return x + x_in

    return NAFNetImpl


def __getattr__(name):
    if name == "NAFNet":
        cls = _build_nafnet_class()
        globals()["NAFNet"] = cls
        return cls
    raise AttributeError(name)
