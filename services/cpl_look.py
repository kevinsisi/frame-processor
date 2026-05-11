"""CPL Look / anti-glare post-processing.

This approximates a circular polarizer look after capture, tuned for car interiors:
black gloss trim, instrument glass, center screens, and window glare. It cannot
recover detail destroyed by glare, but it can reduce bright low-saturation
reflections and deepen color separation without changing the original file.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from models.enums import CplStrength


@dataclass(frozen=True)
class _CplProfile:
    glare_reduction: float
    local_contrast: float
    vibrance: float
    sky_deepen: float


_PROFILES: dict[CplStrength, _CplProfile] = {
    CplStrength.LOW: _CplProfile(glare_reduction=0.18, local_contrast=0.0, vibrance=0.04, sky_deepen=0.05),
    CplStrength.MEDIUM: _CplProfile(glare_reduction=0.32, local_contrast=0.0, vibrance=0.07, sky_deepen=0.10),
    CplStrength.HIGH: _CplProfile(glare_reduction=0.46, local_contrast=0.0, vibrance=0.09, sky_deepen=0.16),
}


def apply_cpl_look(image: Image.Image, strength: CplStrength) -> Image.Image:
    if strength is CplStrength.NONE:
        return image.convert("RGB")

    profile = _PROFILES[strength]
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[..., 0]
    saturation = hsv[..., 1]
    value = hsv[..., 2]
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    local_luma = cv2.medianBlur(np.clip(luma * 255.0, 0, 255).astype(np.uint8), 11).astype(np.float32) / 255.0
    specular_excess = _soft_mask((luma - local_luma - 0.025) / 0.16)

    glare_mask = (
        _soft_mask((luma - 0.68) / 0.24)
        * _soft_mask((0.50 - saturation) / 0.34)
        * specular_excess
    )
    skin_mask = _skin_protection_mask(hue, saturation, value)
    glare_mask *= 1.0 - skin_mask * 0.75

    adjusted = rgb * (1.0 - glare_mask[..., None] * profile.glare_reduction)
    adjusted = _add_local_contrast(adjusted, amount=profile.local_contrast)

    hsv_adjusted = cv2.cvtColor(np.clip(adjusted, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    saturation_boost = 1.0 + profile.vibrance * (1.0 - hsv_adjusted[..., 1]) * (1.0 - skin_mask * 0.6)
    hsv_adjusted[..., 1] = np.clip(hsv_adjusted[..., 1] * saturation_boost, 0.0, 1.0)

    sky_mask = _sky_mask(hsv_adjusted[..., 0], hsv_adjusted[..., 1], hsv_adjusted[..., 2])
    hsv_adjusted[..., 1] = np.clip(hsv_adjusted[..., 1] * (1.0 + sky_mask * profile.sky_deepen), 0.0, 1.0)
    hsv_adjusted[..., 2] = np.clip(hsv_adjusted[..., 2] * (1.0 - sky_mask * profile.sky_deepen * 0.35), 0.0, 1.0)

    out = cv2.cvtColor(hsv_adjusted, cv2.COLOR_HSV2RGB)
    return Image.fromarray(np.clip(out * 255.0, 0, 255).astype(np.uint8), "RGB")


def _soft_mask(values: np.ndarray) -> np.ndarray:
    return np.clip(values, 0.0, 1.0)


def _add_local_contrast(rgb: np.ndarray, *, amount: float) -> np.ndarray:
    if amount <= 0:
        return rgb
    blurred = cv2.GaussianBlur(rgb, (0, 0), sigmaX=7.0, sigmaY=7.0)
    detail = rgb - blurred
    return np.clip(rgb + detail * amount, 0.0, 1.0)


def _skin_protection_mask(hue: np.ndarray, saturation: np.ndarray, value: np.ndarray) -> np.ndarray:
    warm_hue = ((hue >= 0.0) & (hue <= 45.0)) | (hue >= 335.0)
    mask = warm_hue & (saturation >= 0.12) & (saturation <= 0.68) & (value >= 0.20) & (value <= 0.96)
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigmaX=2.5, sigmaY=2.5)


def _sky_mask(hue: np.ndarray, saturation: np.ndarray, value: np.ndarray) -> np.ndarray:
    blue_hue = (hue >= 185.0) & (hue <= 255.0)
    mask = blue_hue & (saturation >= 0.18) & (saturation <= 0.72) & (value >= 0.45)
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigmaX=5.0, sigmaY=5.0)
