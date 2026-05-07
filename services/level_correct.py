"""水平校正（v0.2.0 實作 — Hough line heuristic）。

策略：

1. 灰階 → Canny edge → HoughLinesP 找線段
2. 過濾出近水平線段（角度 |θ| ≤ 30°）
3. 取中位數角度作為校正量
4. 超過閾值（預設 ±5°）視為誤判，回傳 0 不旋轉
5. 角度太小（< 0.2°）也不旋轉，省 IO 與品質損失

回傳 ``(rotated_image, applied_degrees)``：``applied_degrees == 0.0`` 代表沒做動作。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np
from PIL import Image

if TYPE_CHECKING:
    pass


_MIN_DEGREES = 0.2
_DEFAULT_MAX_DEGREES = 5.0
_HORIZONTAL_BAND_DEGREES = 30.0


def correct_level(
    image: Image.Image,
    *,
    threshold_deg: float = _DEFAULT_MAX_DEGREES,
) -> tuple[Image.Image, float]:
    """偵測主水平線並旋轉。

    旋轉量超過 ``threshold_deg`` 視為誤判，原圖回傳。
    """

    rgb = image.convert("RGB")
    arr = np.asarray(rgb)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Canny 預設參數對自然光照片表現穩定
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    h, w = gray.shape
    short_edge = min(h, w)
    hough_threshold = max(50, int(short_edge * 0.25))
    min_line_length = max(40, int(short_edge * 0.30))
    max_line_gap = 20

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=hough_threshold,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )
    if lines is None or len(lines) == 0:
        return rgb, 0.0

    angles: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if abs(angle) <= _HORIZONTAL_BAND_DEGREES:
            angles.append(angle)

    if not angles:
        return rgb, 0.0

    median_angle = float(np.median(angles))
    if abs(median_angle) > threshold_deg:
        return rgb, 0.0
    if abs(median_angle) < _MIN_DEGREES:
        return rgb, 0.0

    rotated = rgb.rotate(median_angle, resample=Image.BICUBIC, expand=False, fillcolor=(0, 0, 0))
    return rotated, median_angle
