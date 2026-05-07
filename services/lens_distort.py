"""鏡頭桶形畸變矯正（barrel distortion correction）。

車輛照片常用廣角鏡頭（手機、行車記錄器、24mm 廣角）會有桶形畸變：
畫面邊緣外擴、車身線條呈弓形。OpenCV 的 ``undistort`` 用 Brown-Conrady 模型反向矯正。

實作策略：
- 沒有實際 EXIF 鏡頭參數，用通用「中度廣角」預設係數 (k1, k2)，可在 settings 調整
- 焦距 f 設為 max(w, h)（pinhole 假設）；主點放在影像中心
- ``cv2.getOptimalNewCameraMatrix`` 把矯正後仍然有效的區域當作裁切框，去掉外擴黑邊

公開介面：``correct_distortion(image: PIL.Image) -> PIL.Image``
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from api.config import settings


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
    return Image.fromarray(undistorted)
