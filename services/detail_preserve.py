"""Luma-only detail preservation after denoise/chroma cleanup.

This step does not hallucinate texture. It nudges structured processed luma back
toward source luma only where the source contains bounded high-frequency detail.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from models.enums import DetailPreserveStrength


@dataclass(frozen=True)
class _Profile:
    amount: float
    max_delta: float
    structure_floor: float


_PROFILES: dict[DetailPreserveStrength, _Profile] = {
    DetailPreserveStrength.LOW: _Profile(amount=0.46, max_delta=9.0, structure_floor=4.5),
    DetailPreserveStrength.MEDIUM: _Profile(amount=0.62, max_delta=12.0, structure_floor=4.0),
    DetailPreserveStrength.HIGH: _Profile(amount=0.76, max_delta=14.0, structure_floor=3.5),
}


def apply_detail_preserve(
    source: Image.Image,
    processed: Image.Image,
    strength: DetailPreserveStrength,
) -> Image.Image:
    if strength is DetailPreserveStrength.NONE:
        return processed

    profile = _PROFILES[strength]
    source_rgb = np.asarray(source.convert("RGB").resize(processed.size), dtype=np.uint8)
    processed_rgb = np.asarray(processed.convert("RGB"), dtype=np.uint8)

    source_ycrcb = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2YCrCb)
    processed_ycrcb = cv2.cvtColor(processed_rgb, cv2.COLOR_RGB2YCrCb)
    source_y = source_ycrcb[:, :, 0].astype(np.float32)
    processed_y = processed_ycrcb[:, :, 0].astype(np.float32)

    source_base_y = cv2.bilateralFilter(source_y.astype(np.uint8), d=7, sigmaColor=18, sigmaSpace=9).astype(np.float32)
    source_detail_weight = np.clip((np.abs(source_y - source_base_y) - 1.0) / profile.max_delta, 0.0, 1.0)
    luma_delta = np.clip(source_y - processed_y, -profile.max_delta, profile.max_delta)

    blurred_source = cv2.GaussianBlur(source_y, (0, 0), sigmaX=1.0)
    blurred_processed = cv2.GaussianBlur(processed_y, (0, 0), sigmaX=1.0)
    source_grad_x = cv2.Sobel(blurred_source, cv2.CV_32F, 1, 0, ksize=3)
    source_grad_y = cv2.Sobel(blurred_source, cv2.CV_32F, 0, 1, ksize=3)
    processed_grad_x = cv2.Sobel(blurred_processed, cv2.CV_32F, 1, 0, ksize=3)
    processed_grad_y = cv2.Sobel(blurred_processed, cv2.CV_32F, 0, 1, ksize=3)
    source_structure = np.sqrt((source_grad_x * source_grad_x) + (source_grad_y * source_grad_y))
    processed_structure = np.sqrt((processed_grad_x * processed_grad_x) + (processed_grad_y * processed_grad_y))
    structure = cv2.GaussianBlur(np.maximum(source_structure, processed_structure), (0, 0), sigmaX=1.2)
    structure_weight = np.clip((structure - profile.structure_floor) / 28.0, 0.0, 1.0)

    source_local_mean = cv2.GaussianBlur(source_y, (0, 0), sigmaX=4.0)
    dark_structure_allow = structure_weight * np.clip((source_local_mean - 64.0) / 96.0, 0.0, 1.0)
    dark_protect = np.maximum(
        np.clip((source_y - 48.0) / 96.0, 0.0, 1.0),
        dark_structure_allow * 0.85,
    )
    highlight_protect = np.clip((248.0 - source_y) / 32.0, 0.0, 1.0)
    mask = structure_weight * source_detail_weight * dark_protect * highlight_protect
    if float(mask.max(initial=0.0)) <= 0.0:
        return processed

    processed_ycrcb[:, :, 0] = np.clip(processed_y + (luma_delta * mask * profile.amount), 0, 255).astype(np.uint8)
    result = cv2.cvtColor(processed_ycrcb, cv2.COLOR_YCrCb2RGB)
    return Image.fromarray(result, mode="RGB")
