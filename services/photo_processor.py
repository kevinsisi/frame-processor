"""照片處理 pipeline 主入口（v0.2.0）。

Pipeline 順序：``level_correct → auto_crop → color_grade``。
每個階段獨立可關閉；最後輸出 jpg 到 ``<storage>/projects/<pid>/processed/<photo_id>.<preset>.jpg``。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from models.enums import ColorGradePreset
from services import auto_crop, color_grade, level_correct, storage


@dataclass(slots=True)
class ProcessedResult:
    relative_path: Path
    absolute_path: Path
    size_bytes: int
    rotation_degrees: float
    crop_box: tuple[int, int, int, int]


def process_photo(
    *,
    project_id: uuid.UUID,
    photo_id: uuid.UUID,
    source_relative: str | Path,
    preset: ColorGradePreset,
    apply_level_correct: bool = True,
    target_aspect: str = auto_crop.ORIGINAL_ASPECT,
) -> ProcessedResult:
    """跑完整 pipeline 並落地 jpg。原圖永不覆寫。"""

    src_abs = storage.absolute_path(source_relative)
    with Image.open(src_abs) as src:
        # EXIF orientation 必先處理，否則 iPhone / DJI 直拍照片會躺著
        img = ImageOps.exif_transpose(src).convert("RGB")

    rotation = 0.0
    if apply_level_correct:
        img, rotation = level_correct.correct_level(img)

    img, crop_box = auto_crop.auto_crop(img, target_aspect=target_aspect)
    img = color_grade.apply_grade(img, preset)

    abs_path = storage.processed_absolute_path(
        project_id=project_id, photo_id=photo_id, preset=preset
    )
    size = storage.save_processed_jpeg(img, abs_path)
    rel_path = storage.processed_relative_path(
        project_id=project_id, photo_id=photo_id, preset=preset
    )

    return ProcessedResult(
        relative_path=rel_path,
        absolute_path=abs_path,
        size_bytes=size,
        rotation_degrees=rotation,
        crop_box=(crop_box.left, crop_box.top, crop_box.right, crop_box.bottom),
    )
