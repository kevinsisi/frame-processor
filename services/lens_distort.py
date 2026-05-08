"""鏡頭桶形畸變矯正（barrel distortion correction）。

車輛照片常用廣角鏡頭（手機、行車記錄器、24mm 廣角）會有桶形畸變：
畫面邊緣外擴、車身線條呈弓形。OpenCV 的 ``undistort`` 用 Brown-Conrady 模型反向矯正。

實作策略：
- 沒有實際 EXIF 鏡頭參數，用通用「中度廣角」預設係數 (k1, k2)，可在 settings 調整
- 焦距 f 設為 max(w, h)（pinhole 假設）；主點放在影像中心
- ``cv2.getOptimalNewCameraMatrix`` 把矯正後仍然有效的區域當作裁切框，去掉外擴黑邊
- 再用 Hough line 偵測左右兩側近垂直線是否向上收斂；若有，做自動垂直透視修正

公開介面：``correct_distortion(image: PIL.Image) -> PIL.Image``
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from api.config import settings

MAX_VERTICAL_PERSPECTIVE_INSET_RATIO = 0.18
MIN_VERTICAL_LINE_RATIO = 0.12
VERTICAL_LINE_MAX_SLOPE = 0.75
VERTICAL_PERSPECTIVE_MIN_SLOPE = 0.025


def correct_distortion(image: Image.Image) -> Image.Image:
    rgb = np.array(image.convert("RGB"))
    h, w = rgb.shape[:2]
    k1 = float(settings.lens_distort_k1)
    k2 = float(settings.lens_distort_k2)
    if abs(k1) < 1e-6 and abs(k2) < 1e-6:
        return image

    focal = float(max(w, h))
    camera_matrix = np.array(
        [[focal, 0.0, w / 2.0], [0.0, focal, h / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    dist_coeffs = np.array([k1, k2, 0.0, 0.0, 0.0], dtype=np.float64)

    new_matrix, valid_roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeffs, (w, h), alpha=0.0, newImgSize=(w, h)
    )
    undistorted = cv2.undistort(rgb, camera_matrix, dist_coeffs, None, new_matrix)

    x, y, rw, rh = valid_roi
    if rw > 0 and rh > 0:
        undistorted = undistorted[y : y + rh, x : x + rw]
    inset = _estimate_vertical_perspective_inset(undistorted)
    if inset > 0:
        undistorted = _correct_vertical_perspective(undistorted, inset)
    return Image.fromarray(undistorted)


def _estimate_vertical_perspective_inset(rgb: np.ndarray) -> float:
    source_h, source_w = rgb.shape[:2]
    scale = 1.0
    max_edge = max(source_w, source_h)
    if max_edge > 900:
        scale = 900 / max_edge
        rgb = cv2.resize(
            rgb,
            (max(1, round(source_w * scale)), max(1, round(source_h * scale))),
            interpolation=cv2.INTER_AREA,
        )
    h, w = rgb.shape[:2]
    if h < 80 or w < 80:
        return 0.0
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 60, 160)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=max(30, min(w, h) // 8),
        minLineLength=max(40, int(h * MIN_VERTICAL_LINE_RATIO)),
        maxLineGap=max(8, min(w, h) // 40),
    )
    if lines is None:
        return 0.0

    left_slopes: list[float] = []
    right_slopes: list[float] = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dy = float(y2 - y1)
        dx = float(x2 - x1)
        if abs(dy) < h * MIN_VERTICAL_LINE_RATIO:
            continue
        slope = dx / dy
        if abs(slope) > VERTICAL_LINE_MAX_SLOPE:
            continue
        mid_x = (x1 + x2) / 2
        length = float(np.hypot(dx, dy))
        weighted_slope = slope * min(2.0, length / max(h * 0.35, 1.0))
        if mid_x < w * 0.46:
            left_slopes.append(weighted_slope)
        elif mid_x > w * 0.54:
            right_slopes.append(weighted_slope)

    if len(left_slopes) < 2 or len(right_slopes) < 2:
        return 0.0
    left = float(np.median(left_slopes))
    right = float(np.median(right_slopes))
    if not (left < -VERTICAL_PERSPECTIVE_MIN_SLOPE and right > VERTICAL_PERSPECTIVE_MIN_SLOPE):
        return 0.0
    convergence = (abs(left) + abs(right)) / 2
    inset = convergence * h * 0.55
    if inset < w * 0.015:
        return 0.0
    capped = min(inset, w * MAX_VERTICAL_PERSPECTIVE_INSET_RATIO)
    return float(capped / scale)


def _correct_vertical_perspective(rgb: np.ndarray, inset: float) -> np.ndarray:
    h, w = rgb.shape[:2]
    inset = float(np.clip(inset, 0.0, w * MAX_VERTICAL_PERSPECTIVE_INSET_RATIO))
    if inset <= 0:
        return rgb
    src = np.float32([[inset, 0], [w - inset, 0], [w, h], [0, h]])
    dst = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        rgb,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
