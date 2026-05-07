"""自動裁剪（v0.2.0 — energy-based heuristic，無 AI）。

依目標比例在 Sobel 邊緣能量圖上找最高能量 sub-window，回傳裁剪後 PIL Image
與 ``CropBox``。``target_aspect == "original"`` 視為 no-op。

實作：integral image（cumsum）使 sliding window sum O(W·H)。

支援目標比例：``original / 3:2 / 4:3 / 16:9 / 1:1 / 9:16``
v0.4 會用 YOLO 主體偵測 + 三分構圖規則取代這份 heuristic。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import cv2
import numpy as np
from PIL import Image

ORIGINAL_ASPECT: Final = "original"

_ASPECT_RATIOS: Final[dict[str, float]] = {
    "3:2": 3.0 / 2.0,
    "4:3": 4.0 / 3.0,
    "16:9": 16.0 / 9.0,
    "1:1": 1.0,
    "9:16": 9.0 / 16.0,
}


@dataclass(slots=True)
class CropBox:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def supported_aspects() -> list[str]:
    return [ORIGINAL_ASPECT, *_ASPECT_RATIOS.keys()]


def auto_crop(image: Image.Image, target_aspect: str = ORIGINAL_ASPECT) -> tuple[Image.Image, CropBox]:
    """裁剪到 ``target_aspect``。``original`` 直接回傳原圖（不裁）。"""

    rgb = image.convert("RGB")
    w, h = rgb.size

    if target_aspect == ORIGINAL_ASPECT:
        return rgb, CropBox(0, 0, w, h)

    if target_aspect not in _ASPECT_RATIOS:
        raise ValueError(f"unsupported target_aspect: {target_aspect!r}")

    target_ratio = _ASPECT_RATIOS[target_aspect]
    target_w, target_h = _fit_window(w, h, target_ratio)
    if target_w >= w and target_h >= h:
        return rgb, CropBox(0, 0, w, h)

    energy = _compute_energy(np.asarray(rgb))
    box = _find_max_energy_window(energy, target_w, target_h)
    cropped = rgb.crop((box.left, box.top, box.right, box.bottom))
    return cropped, box


def _fit_window(img_w: int, img_h: int, target_ratio: float) -> tuple[int, int]:
    """在 (img_w, img_h) 內找最大內接矩形使其長寬比 = target_ratio。"""
    img_ratio = img_w / img_h
    if img_ratio >= target_ratio:
        # 圖片比 target 寬：高度 = img_h，寬 = img_h * ratio
        out_h = img_h
        out_w = round(out_h * target_ratio)
    else:
        out_w = img_w
        out_h = round(out_w / target_ratio)
    return out_w, out_h


def _compute_energy(rgb_arr: np.ndarray) -> np.ndarray:
    """Sobel 邊緣強度作為「能量」。"""
    gray = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY)
    sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return np.sqrt(sx * sx + sy * sy)


def _find_max_energy_window(energy: np.ndarray, win_w: int, win_h: int) -> CropBox:
    """在 ``energy`` 上找尺寸 ``(win_h, win_w)`` 的最大總能量視窗。"""
    h, w = energy.shape
    win_w = min(win_w, w)
    win_h = min(win_h, h)

    # integral image：iimg[y, x] = sum(energy[0:y, 0:x])
    iimg = np.zeros((h + 1, w + 1), dtype=np.float64)
    iimg[1:, 1:] = np.cumsum(np.cumsum(energy, axis=0), axis=1)

    # window sums via inclusion-exclusion
    bottom = iimg[win_h:, :]   # shape (h - win_h + 1, w + 1)
    top = iimg[:-win_h, :]
    horiz = bottom - top       # shape (h - win_h + 1, w + 1)
    right = horiz[:, win_w:]   # shape (h - win_h + 1, w - win_w + 1)
    left = horiz[:, :-win_w]
    sums = right - left

    flat_idx = int(np.argmax(sums))
    rows = sums.shape[1]
    y = flat_idx // rows
    x = flat_idx % rows

    return CropBox(left=int(x), top=int(y), right=int(x + win_w), bottom=int(y + win_h))
