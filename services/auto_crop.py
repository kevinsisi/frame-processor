"""自動構圖裁剪（stub，v0.4.0 才實作）。

預期介面：``auto_crop(image, target_aspect) -> CropBox``。

實作策略：YOLOv8 偵測車輛主體 + 三分構圖規則 + 主體保持 70% 完整度約束。
"""

from __future__ import annotations


def auto_crop(*args, **kwargs):
    raise NotImplementedError("auto_crop.auto_crop 將在 v0.4.0 實作")
