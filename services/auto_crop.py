"""自動構圖裁剪：YOLOv8n 偵測車輛 + rule-of-thirds 構圖。

策略：
1. 用 ``ultralytics.YOLO("yolov8n.pt")`` 偵測 COCO car (2) / truck (7) / bus (5) / motorcycle (3)
2. 取信心度最高的 bbox 作為主體
3. 若 ``target_aspect`` 是 ORIGINAL 或沒抓到車：原圖回傳
4. 否則計算「最大可行裁剪框」：以主體中心為基準，按 target aspect 從原圖內畫最大矩形，
   並把主體中心對齊到 rule-of-thirds 第三線交點（左下 1/3, 1/3 或右下 2/3, 1/3 視主體位置）
5. 主體必須 100% 落在裁剪框內；不夠空間就退回置中

公開介面：``auto_crop(image, target_aspect) -> PIL.Image``

模型權重 lazy download：首次呼叫時 ultralytics 自動下載 ``yolov8n.pt`` 到
``ULTRALYTICS_DIR``（容器內 ``/data/models-weights/ultralytics``）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from models.enums import ASPECT_RATIO_VALUES, AspectRatio

if TYPE_CHECKING:
    from ultralytics import YOLO  # noqa: F401

VEHICLE_CLASSES = {2, 3, 5, 7}  # COCO: car, motorcycle, bus, truck

_yolo_model = None


def _get_model():
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model
    from ultralytics import YOLO

    weights_dir = Path(
        os.environ.get("ULTRALYTICS_DIR", str(Path.home() / ".ultralytics"))
    )
    weights_dir.mkdir(parents=True, exist_ok=True)
    weights_path = weights_dir / "yolov8n.pt"
    _yolo_model = YOLO(str(weights_path) if weights_path.exists() else "yolov8n.pt")
    return _yolo_model


@dataclass(frozen=True)
class _BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def cx(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def cy(self) -> int:
        return (self.y1 + self.y2) // 2


def auto_crop(image: Image.Image, target_aspect: AspectRatio) -> Image.Image:
    if target_aspect is AspectRatio.ORIGINAL:
        return image
    target = ASPECT_RATIO_VALUES[target_aspect]
    if target is None:
        return image

    rgb = image.convert("RGB")
    bbox = _detect_main_vehicle(rgb)
    w, h = rgb.size
    crop_w, crop_h = _largest_box_in(w, h, target)
    if bbox is None:
        return _center_crop(rgb, crop_w, crop_h)

    cx, cy = _rule_of_thirds_anchor(w, h, crop_w, crop_h, bbox)
    x0 = _clamp(cx - crop_w // 2, 0, w - crop_w)
    y0 = _clamp(cy - crop_h // 2, 0, h - crop_h)

    x0, y0 = _ensure_subject_inside(x0, y0, crop_w, crop_h, bbox, w, h)
    return rgb.crop((x0, y0, x0 + crop_w, y0 + crop_h))


def _detect_main_vehicle(image: Image.Image) -> _BBox | None:
    model = _get_model()
    arr = np.array(image)
    results = model.predict(arr, verbose=False, conf=0.25)
    if not results:
        return None
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return None

    best: _BBox | None = None
    best_conf = -1.0
    for i in range(len(boxes)):
        cls = int(boxes.cls[i].item())
        if cls not in VEHICLE_CLASSES:
            continue
        conf = float(boxes.conf[i].item())
        if conf <= best_conf:
            continue
        x1, y1, x2, y2 = boxes.xyxy[i].tolist()
        best = _BBox(int(x1), int(y1), int(x2), int(y2))
        best_conf = conf
    return best


def _largest_box_in(w: int, h: int, target: tuple[int, int]) -> tuple[int, int]:
    """在 (w, h) 內畫出 target aspect 的最大矩形。"""
    tw, th = target
    if w * th >= h * tw:
        crop_h = h
        crop_w = int(round(h * tw / th))
    else:
        crop_w = w
        crop_h = int(round(w * th / tw))
    return min(crop_w, w), min(crop_h, h)


def _center_crop(image: Image.Image, crop_w: int, crop_h: int) -> Image.Image:
    w, h = image.size
    x0 = (w - crop_w) // 2
    y0 = (h - crop_h) // 2
    return image.crop((x0, y0, x0 + crop_w, y0 + crop_h))


def _rule_of_thirds_anchor(
    img_w: int, img_h: int, crop_w: int, crop_h: int, bbox: _BBox
) -> tuple[int, int]:
    """選擇 rule-of-thirds 交點：水平靠近主體在圖中的左/右側，垂直放下三分之一處。"""
    horizontal = "left" if bbox.cx < img_w / 2 else "right"
    if horizontal == "left":
        anchor_x_in_crop = crop_w // 3
    else:
        anchor_x_in_crop = crop_w * 2 // 3
    anchor_y_in_crop = crop_h * 2 // 3
    return bbox.cx - anchor_x_in_crop + crop_w // 2, bbox.cy - anchor_y_in_crop + crop_h // 2


def _ensure_subject_inside(
    x0: int, y0: int, crop_w: int, crop_h: int, bbox: _BBox, img_w: int, img_h: int
) -> tuple[int, int]:
    if bbox.x1 < x0:
        x0 = max(bbox.x1, 0)
    if bbox.x2 > x0 + crop_w:
        x0 = min(bbox.x2 - crop_w, img_w - crop_w)
    if bbox.y1 < y0:
        y0 = max(bbox.y1, 0)
    if bbox.y2 > y0 + crop_h:
        y0 = min(bbox.y2 - crop_h, img_h - crop_h)
    return _clamp(x0, 0, img_w - crop_w), _clamp(y0, 0, img_h - crop_h)


def _clamp(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v
