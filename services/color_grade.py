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
    balanced = _gray_world_white_balance(image)
    neutral = _channel_shift(balanced, r_delta=5, g_delta=-3, b_delta=-2)
    toned = _showroom_tone_curve(neutral)
    softened = ImageEnhance.Contrast(toned).enhance(0.86)
    clarified = softened.filter(ImageFilter.UnsharpMask(radius=1.4, percent=38, threshold=6))
    return _reduce_purple_magenta(clarified)


def _showroom_tone_curve(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    shadows = np.clip((0.78 - luma) / 0.78, 0.0, 1.0) ** 1.7
    whites = np.clip((luma - 0.62) / 0.38, 0.0, 1.0) ** 1.4
    rgb = rgb * 1.10
    rgb = rgb + shadows[..., np.newaxis] * 0.10
    rgb = rgb + whites[..., np.newaxis] * 0.035
    return Image.fromarray(np.clip(rgb * 255.0, 0, 255).astype(np.uint8), "RGB")


def _reduce_purple_magenta(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[..., 0]
    saturation = hsv[..., 1]
    purple_magenta = ((hue >= 260.0) & (hue <= 335.0)).astype(np.float32)
    saturated_color = np.clip((saturation - 0.18) / 0.42, 0.0, 1.0)
    reduction = 1.0 - (purple_magenta * saturated_color * 0.45)
    hsv[..., 1] = saturation * reduction
    out = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return Image.fromarray(np.clip(out * 255.0, 0, 255).astype(np.uint8), "RGB")


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
