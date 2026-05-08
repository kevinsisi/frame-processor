"""NAFNet 影像降噪。

模型：NAFNet-SIDD-width32（小型 SIDD 預訓練版本，~17M params，CPU 可用）。
參考論文：Chen et al. "Simple Baselines for Image Restoration" (ECCV 2022).

策略：
- PyTorch 直接定義 NAFNet 架構（不依賴 basicsr，避免 BasicSR 巨型相依）
- 權重 lazy download：第一次呼叫時從 HuggingFace mirror 下載到 NAFNET_DIR
- CPU 推理：對 > tile 的圖切 tile（預設 512x512 with 32px overlap），最後拼回去
- GPU：``torch.cuda.is_available()`` 自動偵測
- 強度（DenoiseStrength）：light/medium/heavy 用 ``alpha * denoised + (1-alpha) * original``
  混合 (0.4 / 0.7 / 1.0)，避免「過度降噪導致細節糊掉」

公開介面：``denoise(image: PIL.Image, strength: DenoiseStrength) -> PIL.Image``
"""

from __future__ import annotations

import os
import shutil
import urllib.request
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image

from api.config import settings
from models.enums import DenoiseStrength

NAFNET_WEIGHTS_URL = os.environ.get(
    "NAFNET_WEIGHTS_URL",
    "https://huggingface.co/JingyunLiang/NAFNet/resolve/main/NAFNet-SIDD-width32.pth",
)
NAFNET_WEIGHTS_FILENAME = "NAFNet-SIDD-width32.pth"

STRENGTH_BLEND: dict[DenoiseStrength, float] = {
    DenoiseStrength.NONE: 0.0,
    DenoiseStrength.LIGHT: 0.4,
    DenoiseStrength.MEDIUM: 0.7,
    DenoiseStrength.HEAVY: 1.0,
}

_model = None
_device = None
_model_lock = Lock()


class DenoiseError(RuntimeError):
    pass


def denoise(image: Image.Image, strength: DenoiseStrength) -> Image.Image:
    if strength is DenoiseStrength.NONE:
        return image
    alpha = STRENGTH_BLEND[strength]
    rgb = np.array(image.convert("RGB"), dtype=np.float32) / 255.0
    try:
        denoised = _run_nafnet(rgb)
    except DenoiseError:
        denoised = _run_opencv_denoise(rgb, strength)
    blended = alpha * denoised + (1.0 - alpha) * rgb
    blended = np.clip(blended * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(blended)


def _run_opencv_denoise(rgb: np.ndarray, strength: DenoiseStrength) -> np.ndarray:
    """Fallback when NAFNet weights are unavailable in the deploy environment."""

    import cv2

    h_value = {
        DenoiseStrength.LIGHT: 7,
        DenoiseStrength.MEDIUM: 14,
        DenoiseStrength.HEAVY: 24,
    }.get(strength, 0)
    if h_value <= 0:
        return rgb
    image_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(image_u8, cv2.COLOR_RGB2BGR)
    denoised = cv2.fastNlMeansDenoisingColored(
        bgr,
        None,
        h=h_value,
        hColor=max(h_value, 4),
        templateWindowSize=7,
        searchWindowSize=21,
    )
    return cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


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
        with urllib.request.urlopen(NAFNET_WEIGHTS_URL, timeout=120) as resp, tmp.open("wb") as out:
            shutil.copyfileobj(resp, out)
        tmp.replace(target)
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise DenoiseError(
            f"failed to download NAFNet weights from {NAFNET_WEIGHTS_URL}: {exc}"
        ) from exc
    return target


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
