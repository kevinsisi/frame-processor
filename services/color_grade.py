"""色調預設（純 Pillow，無 AI）。

三組 preset：
- ``SHOWROOM_WHITE`` 展示間白：gray-world 白平衡 + 提亮 + 降飽和
- ``OUTDOOR_WARM`` 戶外暖調：暖色偏移 + 對比 + 飽和
- ``NIGHT_COLD`` 夜拍冷調：冷色偏移 + 提暗部 + 對比

公開介面：``apply_grade(image: PIL.Image, preset: ColorGradePreset) -> PIL.Image``
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from models.enums import ColorGradePreset

SHOWROOM_WHITE_POST_CONTRAST_FACTOR = 1.40
SHOWROOM_WHITE_DITHER_STRENGTH = 2.5


def apply_grade(image: Image.Image, preset: ColorGradePreset) -> Image.Image:
    image = image.convert("RGB")
    if preset is ColorGradePreset.SHOWROOM_WHITE:
        return _showroom_white(image)
    if preset is ColorGradePreset.OUTDOOR_WARM:
        return _outdoor_warm(image)
    if preset is ColorGradePreset.NIGHT_COLD:
        return _night_cold(image)
    raise ValueError(f"unsupported preset: {preset}")


def _showroom_white(image: Image.Image) -> Image.Image:
    source_rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    balanced = _gray_world_white_balance(image)
    neutral = _channel_shift(balanced, r_delta=-1, g_delta=1, b_delta=2)
    rgb = np.asarray(neutral.convert("RGB"), dtype=np.float32) / 255.0
    rgb = _showroom_tone_curve(rgb)
    rgb = _pil_contrast_factor(rgb, factor=0.86)
    rgb = _clarify_luma_only(rgb)
    rgb = _reduce_purple_magenta(rgb)
    pre_boost_y = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    rgb = _boost_luma_contrast(rgb, factor=SHOWROOM_WHITE_POST_CONTRAST_FACTOR)
    rgb = _dither_smooth_neutral_luma(rgb, pre_boost_y=pre_boost_y)
    rgb = _preserve_true_white_anchor(rgb, source_rgb=source_rgb)
    return Image.fromarray(np.clip(rgb * 255.0, 0, 255).astype(np.uint8), "RGB")


def _showroom_tone_curve(rgb: np.ndarray) -> np.ndarray:
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    shadows = np.clip((0.78 - luma) / 0.78, 0.0, 1.0) ** 1.7
    whites = np.clip((luma - 0.62) / 0.38, 0.0, 1.0) ** 1.4
    highlight_guard = _smoothstep(0.78, 0.98, luma)
    out = rgb * (1.10 - (0.19 * highlight_guard[..., np.newaxis]))
    out = out + shadows[..., np.newaxis] * 0.10
    out = out + whites[..., np.newaxis] * (1.0 - highlight_guard[..., np.newaxis]) * 0.035
    return np.clip(out, 0.0, 0.995)


def _pil_contrast_factor(rgb: np.ndarray, *, factor: float) -> np.ndarray:
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    mean = float(luma.mean())
    return np.clip(rgb * factor + mean * (1.0 - factor), 0.0, 1.0)


def _reduce_purple_magenta(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(np.clip(rgb, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hue = hsv[..., 0]
    saturation = hsv[..., 1]
    purple_magenta = ((hue >= 260.0) & (hue <= 335.0)).astype(np.float32)
    saturated_color = np.clip((saturation - 0.18) / 0.42, 0.0, 1.0)
    reduction = 1.0 - (purple_magenta * saturated_color * 0.45)
    hsv[..., 1] = saturation * reduction
    out = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return np.clip(out, 0.0, 1.0)


def _clarify_luma_only(rgb: np.ndarray) -> np.ndarray:
    rgb_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    ycrcb = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2YCrCb)
    y = Image.fromarray(ycrcb[:, :, 0], mode="L")
    ycrcb[:, :, 0] = np.asarray(y.filter(ImageFilter.UnsharpMask(radius=1.4, percent=34, threshold=7)))
    out = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2RGB)
    return out.astype(np.float32) / 255.0


def _boost_luma_contrast(rgb: np.ndarray, *, factor: float) -> np.ndarray:
    ycrcb = cv2.cvtColor(np.clip(rgb, 0.0, 1.0), cv2.COLOR_RGB2YCrCb)
    y = ycrcb[..., 0]
    pivot = float(y.mean())
    midtone_weight = _smoothstep(0.04, 0.22, y) * (1.0 - _smoothstep(0.84, 0.985, y))
    local_factor = 1.0 + ((factor - 1.0) * midtone_weight)
    boosted = pivot + ((y - pivot) * local_factor)
    ycrcb[..., 0] = _soft_clip_luma(boosted)
    out = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2RGB)
    return np.clip(out, 0.0, 1.0)


def _smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - (2.0 * t))


def _soft_clip_luma(y: np.ndarray) -> np.ndarray:
    out = y.copy()
    high = out > 0.91
    if np.any(high):
        high_base = 0.91
        high_span = 0.082
        high_scale = 0.07
        normalized = 1.0 - np.exp(-(out[high] - high_base) / high_scale)
        normalized_max = 1.0 - np.exp(-(1.0 - high_base) / high_scale)
        out[high] = high_base + (normalized / normalized_max) * high_span
    low = out < 0.018
    out[low] = 0.018 - (1.0 - np.exp(-(0.018 - out[low]) / 0.025)) * 0.012
    return np.clip(out, 0.0, 0.992)


def _preserve_true_white_anchor(rgb: np.ndarray, *, source_rgb: np.ndarray) -> np.ndarray:
    source_y = 0.299 * source_rgb[..., 0] + 0.587 * source_rgb[..., 1] + 0.114 * source_rgb[..., 2]
    source_chroma = np.max(source_rgb, axis=2) - np.min(source_rgb, axis=2)
    white_weight = _smoothstep(0.992, 1.0, source_y) * (1.0 - np.clip(source_chroma / 0.04, 0.0, 1.0))
    if float(white_weight.max(initial=0.0)) <= 0.0:
        return rgb
    ycrcb = cv2.cvtColor(np.clip(rgb, 0.0, 1.0), cv2.COLOR_RGB2YCrCb)
    current_y = ycrcb[..., 0]
    anchor_floor = 0.985 + (0.015 * _smoothstep(0.995, 1.0, source_y))
    floored_y = np.maximum(current_y, anchor_floor)
    ycrcb[..., 0] = (current_y * (1.0 - white_weight)) + (floored_y * white_weight)
    out = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2RGB)
    return np.clip(out, 0.0, 1.0)


def _dither_smooth_neutral_luma(rgb: np.ndarray, *, pre_boost_y: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(np.clip(rgb, 0.0, 1.0), cv2.COLOR_RGB2YCrCb)
    y = ycrcb[..., 0]
    cr = ycrcb[..., 1]
    cb = ycrcb[..., 2]
    pre_boost_u8_scale = pre_boost_y * 255.0
    local_detail = np.abs(pre_boost_u8_scale - cv2.GaussianBlur(pre_boost_u8_scale, (0, 0), sigmaX=1.2))
    chroma_u8_scale = np.sqrt((((cr - 0.5) * 255.0) ** 2) + (((cb - 0.5) * 255.0) ** 2))
    smooth_weight = 1.0 - np.clip(local_detail / 3.0, 0.0, 1.0)
    neutral_weight = 1.0 - np.clip((chroma_u8_scale - 4.0) / 26.0, 0.0, 1.0)
    weight = smooth_weight * neutral_weight
    if float(weight.max(initial=0.0)) <= 0.0:
        return rgb
    yy, xx = np.indices(y.shape)
    noise_raw = np.sin((xx * 12.9898) + (yy * 78.233)) * 43758.5453
    noise = (noise_raw - np.floor(noise_raw) - 0.5) * (SHOWROOM_WHITE_DITHER_STRENGTH / 255.0)
    ycrcb[..., 0] = np.clip(y + noise * weight, 0.0, 1.0)
    out = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2RGB)
    return np.clip(out, 0.0, 1.0)


def _outdoor_warm(image: Image.Image) -> Image.Image:
    warmed = _channel_shift(image, r_delta=30, g_delta=8, b_delta=-24)
    contrasted = ImageEnhance.Contrast(warmed).enhance(1.2)
    saturated = ImageEnhance.Color(contrasted).enhance(1.24)
    return saturated


def _night_cold(image: Image.Image) -> Image.Image:
    cooled = _channel_shift(image, r_delta=-18, g_delta=-2, b_delta=28)
    lifted = _gamma_lift_shadows(cooled, gamma=0.82)
    contrasted = ImageEnhance.Contrast(lifted).enhance(1.14)
    return ImageEnhance.Color(contrasted).enhance(0.92)


def _gray_world_white_balance(image: Image.Image) -> Image.Image:
    """Gray-world 假設：場景 R/G/B 平均值應該相等。對偏色光源做平衡。"""
    r, g, b = image.split()
    r_mean = _band_mean(r)
    g_mean = _band_mean(g)
    b_mean = _band_mean(b)
    target = (r_mean + g_mean + b_mean) / 3.0
    if target <= 0:
        return image
    r = r.point(lambda v, k=target / max(r_mean, 1.0): _clamp(v * k))
    g = g.point(lambda v, k=target / max(g_mean, 1.0): _clamp(v * k))
    b = b.point(lambda v, k=target / max(b_mean, 1.0): _clamp(v * k))
    return Image.merge("RGB", (r, g, b))


def _channel_shift(
    image: Image.Image, *, r_delta: int, g_delta: int, b_delta: int
) -> Image.Image:
    r, g, b = image.split()
    r = r.point(lambda v, d=r_delta: _clamp(v + d))
    g = g.point(lambda v, d=g_delta: _clamp(v + d))
    b = b.point(lambda v, d=b_delta: _clamp(v + d))
    return Image.merge("RGB", (r, g, b))


def _gamma_lift_shadows(image: Image.Image, *, gamma: float) -> Image.Image:
    """gamma < 1 提亮暗部，gamma > 1 壓暗部。對 RGB 三通道一致套用。"""
    inv_gamma = 1.0 / gamma
    lut = [_clamp(((i / 255.0) ** inv_gamma) * 255.0) for i in range(256)]
    return ImageOps.autocontrast(image.point(lut * 3), cutoff=0)


def _band_mean(band: Image.Image) -> float:
    histogram = band.histogram()
    total = sum(histogram)
    if total == 0:
        return 0.0
    weighted = sum(i * count for i, count in enumerate(histogram))
    return weighted / total


def _clamp(v: float) -> int:
    if v < 0:
        return 0
    if v > 255:
        return 255
    return int(v)
