"""Dark-area chroma cleanup for false color and color speckle noise.

The effect intentionally edits chroma channels only. Luma stays from the source
image so leather grain, stitching, logos, and edge detail remain intact.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from models.enums import ChromaCleanStrength

_SATURATED_CHROMA_SMOOTHING_FLOOR = 0.08
_SATURATED_SPECKLE_CLEANUP_CEILING = 1.0
_SATURATED_SPECKLE_NEUTRAL_CEILING = 0.45


@dataclass(frozen=True)
class _Profile:
    chroma_blend: float
    neutral_blend: float
    degrid_blend: float
    dark_limit: int
    saturation_protect: int
    nlm_h: int
    median_size: int


_PROFILES: dict[ChromaCleanStrength, _Profile] = {
    ChromaCleanStrength.LOW: _Profile(
        chroma_blend=0.35,
        neutral_blend=0.08,
        degrid_blend=0.45,
        dark_limit=112,
        saturation_protect=110,
        nlm_h=4,
        median_size=3,
    ),
    ChromaCleanStrength.MEDIUM: _Profile(
        chroma_blend=0.58,
        neutral_blend=0.18,
        degrid_blend=0.82,
        dark_limit=132,
        saturation_protect=130,
        nlm_h=6,
        median_size=5,
    ),
    ChromaCleanStrength.HIGH: _Profile(
        chroma_blend=0.78,
        neutral_blend=0.45,
        degrid_blend=0.92,
        dark_limit=150,
        saturation_protect=145,
        nlm_h=8,
        median_size=5,
    ),
}


def apply_chroma_clean(image: Image.Image, strength: ChromaCleanStrength) -> Image.Image:
    if strength is ChromaCleanStrength.NONE:
        return image
    profile = _PROFILES[strength]
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1].astype(np.float32)
    value = hsv[:, :, 2].astype(np.float32)

    dark_weight = np.clip((profile.dark_limit - value) / max(profile.dark_limit, 1), 0.0, 1.0)
    neutral_weight = np.clip(
        (profile.saturation_protect - saturation) / max(profile.saturation_protect, 1),
        0.0,
        1.0,
    )
    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
    y = ycrcb[:, :, 0]
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]

    cr_residual = np.abs(cr.astype(np.float32) - cv2.medianBlur(cr, 3).astype(np.float32))
    cb_residual = np.abs(cb.astype(np.float32) - cv2.medianBlur(cb, 3).astype(np.float32))
    speckle_weight = np.clip((cr_residual + cb_residual - 8.0) / 32.0, 0.0, 1.0)
    saturated_cleanup = _SATURATED_CHROMA_SMOOTHING_FLOOR + (
        (_SATURATED_SPECKLE_CLEANUP_CEILING - _SATURATED_CHROMA_SMOOTHING_FLOOR) * speckle_weight
    )
    # Keep a small smoothing floor for saturated false-color speckles, but do not
    # pull saturated ambient lights, logos, or belts toward neutral chroma.
    mask = dark_weight * (neutral_weight + (1.0 - neutral_weight) * saturated_cleanup)
    if float(mask.max(initial=0.0)) <= 0.0:
        return image

    cr_clean = _clean_chroma_channel(cr, profile)
    cb_clean = _clean_chroma_channel(cb, profile)

    chroma_alpha = mask * profile.chroma_blend
    neutral_alpha = (
        dark_weight
        * (neutral_weight + (1.0 - neutral_weight) * speckle_weight * _SATURATED_SPECKLE_NEUTRAL_CEILING)
        * profile.neutral_blend
    )
    cr_out = _blend_chroma(cr, cr_clean, chroma_alpha, neutral_alpha)
    cb_out = _blend_chroma(cb, cb_clean, chroma_alpha, neutral_alpha)
    cr_out, cb_out = _suppress_dark_chroma_grid(y, cr_out, cb_out, profile)
    result = cv2.cvtColor(np.dstack([y, cr_out, cb_out]).astype(np.uint8), cv2.COLOR_YCrCb2RGB)
    return Image.fromarray(result, mode="RGB")


def _clean_chroma_channel(channel: np.ndarray, profile: _Profile) -> np.ndarray:
    filtered = cv2.fastNlMeansDenoising(channel, None, h=profile.nlm_h, templateWindowSize=7, searchWindowSize=21)
    filtered = cv2.medianBlur(filtered, profile.median_size)
    return cv2.bilateralFilter(filtered, d=5, sigmaColor=20, sigmaSpace=7)


def _blend_chroma(
    original: np.ndarray,
    cleaned: np.ndarray,
    chroma_alpha: np.ndarray,
    neutral_alpha: np.ndarray,
) -> np.ndarray:
    original_f = original.astype(np.float32)
    cleaned_f = cleaned.astype(np.float32)
    blended = original_f * (1.0 - chroma_alpha) + cleaned_f * chroma_alpha
    neutral = 128.0
    blended = blended * (1.0 - neutral_alpha) + neutral * neutral_alpha
    return np.clip(blended, 0, 255).astype(np.uint8)


def _suppress_dark_chroma_grid(
    y: np.ndarray,
    cr: np.ndarray,
    cb: np.ndarray,
    profile: _Profile,
) -> tuple[np.ndarray, np.ndarray]:
    y_f = y.astype(np.float32)
    cr_f = cr.astype(np.float32)
    cb_f = cb.astype(np.float32)
    chroma_magnitude = np.sqrt(((cr_f - 128.0) ** 2) + ((cb_f - 128.0) ** 2))
    dark_weight = np.clip((float(profile.dark_limit) - y_f) / max(float(profile.dark_limit) - 28.0, 1.0), 0.0, 1.0)
    neutral_weight = np.clip((42.0 - chroma_magnitude) / 42.0, 0.0, 1.0)

    smoothed_y = cv2.GaussianBlur(y_f, (0, 0), sigmaX=1.1)
    grad_x = cv2.Sobel(smoothed_y, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(smoothed_y, cv2.CV_32F, 0, 1, ksize=3)
    structure = np.sqrt((grad_x * grad_x) + (grad_y * grad_y))
    flat_weight = 1.0 - np.clip((structure - 3.5) / 24.0, 0.0, 1.0)

    cr_clean = _clean_grid_channel(cr)
    cb_clean = _clean_grid_channel(cb)
    cr_residual = np.abs(cr_f - cr_clean.astype(np.float32))
    cb_residual = np.abs(cb_f - cb_clean.astype(np.float32))
    residual = np.sqrt((cr_residual * cr_residual) + (cb_residual * cb_residual))
    artifact_weight = np.clip((residual - 0.5) / 5.5, 0.0, 1.0)

    alpha = dark_weight * neutral_weight * flat_weight * artifact_weight * profile.degrid_blend
    if float(alpha.max(initial=0.0)) <= 0.0:
        return cr, cb
    alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=0.8)
    alpha *= dark_weight * neutral_weight * flat_weight
    return _blend_chroma_channel(cr, cr_clean, alpha), _blend_chroma_channel(cb, cb_clean, alpha)


def _clean_grid_channel(channel: np.ndarray) -> np.ndarray:
    filtered = cv2.GaussianBlur(channel, (0, 0), sigmaX=1.4)
    filtered = cv2.medianBlur(filtered, 3)
    return cv2.bilateralFilter(filtered, d=5, sigmaColor=16, sigmaSpace=7)


def _blend_chroma_channel(original: np.ndarray, cleaned: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    blended = original.astype(np.float32) * (1.0 - alpha) + cleaned.astype(np.float32) * alpha
    return np.clip(blended, 0, 255).astype(np.uint8)
