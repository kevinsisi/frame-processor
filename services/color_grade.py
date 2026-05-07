"""色調預設（v0.2.0 實作）。

三組 preset：

- ``SHOWROOM_WHITE`` — 展示間白：gray-world 自動白平衡 + 輕度提亮 + 降低飽和
- ``OUTDOOR_WARM`` — 戶外暖調：暖色偏移（R↑、B↓）+ 輕微 vibrance + 加對比
- ``NIGHT_COLD`` — 夜拍冷調：冷色偏移（B↑、R↓）+ gamma 提暗部

實作走 numpy float 空間，避免 Pillow ImageEnhance 對通道分離調整的限制。
單張 6000×4000 RGB JPEG 在 CPU 上約 1.5–3 秒。
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from models.enums import ColorGradePreset


def apply_grade(image: Image.Image, preset: ColorGradePreset) -> Image.Image:
    """把 ``preset`` 套到 RGB 圖上回傳新的 PIL Image。原圖不被修改。"""

    rgb = image.convert("RGB")
    arr = np.asarray(rgb, dtype=np.float32) / 255.0

    if preset is ColorGradePreset.SHOWROOM_WHITE:
        arr = _showroom_white(arr)
    elif preset is ColorGradePreset.OUTDOOR_WARM:
        arr = _outdoor_warm(arr)
    elif preset is ColorGradePreset.NIGHT_COLD:
        arr = _night_cold(arr)
    else:
        raise ValueError(f"unknown preset: {preset!r}")

    arr = np.clip(arr, 0.0, 1.0)
    out = (arr * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(out, mode="RGB")


def _gray_world_wb(arr: np.ndarray) -> np.ndarray:
    """gray-world：假設整張 RGB 平均值應為灰，把每通道 scale 到該平均值。"""
    means = arr.reshape(-1, 3).mean(axis=0)
    target = float(means.mean())
    # 避免極端值：若某通道平均近 0（純黑底圖）就跳過
    safe = np.where(means < 1e-3, target, means)
    scale = target / safe
    return arr * scale


def _apply_contrast(arr: np.ndarray, amount: float) -> np.ndarray:
    """以 0.5 為中心調對比；amount=1.0 不變、>1 加強、<1 變弱。"""
    return (arr - 0.5) * amount + 0.5


def _showroom_white(arr: np.ndarray) -> np.ndarray:
    arr = _gray_world_wb(arr)
    arr = arr * 1.05  # 提亮
    gray = arr.mean(axis=2, keepdims=True)
    arr = gray + (arr - gray) * 0.85  # 降飽和到 85%
    return arr


def _outdoor_warm(arr: np.ndarray) -> np.ndarray:
    arr = arr.copy()
    arr[..., 0] *= 1.08  # R 升
    arr[..., 2] *= 0.95  # B 降
    gray = arr.mean(axis=2, keepdims=True)
    arr = gray + (arr - gray) * 1.10  # vibrance +10%
    arr = _apply_contrast(arr, 1.10)
    return arr


def _night_cold(arr: np.ndarray) -> np.ndarray:
    arr = arr.copy()
    arr[..., 0] *= 0.95  # R 降
    arr[..., 2] *= 1.10  # B 升
    # 提暗部：對 < 0.5 區段套 gamma 0.85（會變亮），亮部不動
    shadow_mask = arr < 0.5
    arr = np.where(shadow_mask, np.power(np.clip(arr, 0.0, 1.0), 0.85), arr)
    return arr
