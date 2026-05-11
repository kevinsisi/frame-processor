"""照片處理 pipeline 主入口。

順序固定：``denoise → lens_distort_correct → level_correct → auto_crop → cpl_look → color_grade``。
為什麼這個順序：
1. **denoise 最先**：geometric ops（warp、resize）會放大噪點 pattern，先洗掉再做幾何
2. **lens_distort 次之**：把廣角桶形修平，後面的 level / crop 才能對得到真水平/真主體
3. **level_correct 第三**：水平校正需要無 fisheye 的圖才能找到真正的地平線
4. **auto_crop 第四**：YOLO 在已校正的圖上偵測車輛 bbox 才準
5. **cpl_look 在色調前**：先壓反光與天空 haze，再讓色調 preset 接手最後一致風格
6. **color_grade 最後**：純像素操作，與幾何無關，最後做不影響先前所有步驟

每階段都會檢查對應參數是否啟用，未啟用直接 pass-through 不做事。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps

from models.enums import (
    AspectRatio,
    ColorGradePreset,
    CplStrength,
    DenoiseStrength,
)
from services import auto_crop, color_grade, cpl_look, denoise, lens_distort, level_correct, storage


@dataclass(frozen=True)
class ProcessedPhoto:
    photo_id: uuid.UUID
    preset: ColorGradePreset
    relative_path: str
    angle_applied: float
    width: int
    height: int


def process_photo(
    *,
    project_id: uuid.UUID,
    photo_id: uuid.UUID,
    source_relative_path: str,
    preset: ColorGradePreset,
    denoise_strength: DenoiseStrength = DenoiseStrength.NONE,
    lens_distort_correct: bool = False,
    level_correct_on: bool = False,
    auto_crop_aspect: AspectRatio | None = None,
    cpl_strength: CplStrength = CplStrength.NONE,
    version_number: int | None = None,
) -> ProcessedPhoto:
    src = storage.absolute_path(source_relative_path)
    with Image.open(src) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")

    if denoise_strength is not DenoiseStrength.NONE:
        img = denoise.denoise(img, denoise_strength)

    if lens_distort_correct:
        img = lens_distort.correct_distortion(img)

    angle_applied = 0.0
    if level_correct_on:
        img, angle_applied = level_correct.correct_level(img)

    if auto_crop_aspect is not None and auto_crop_aspect is not AspectRatio.ORIGINAL:
        img = auto_crop.auto_crop(img, auto_crop_aspect)

    img = _restore_detail_after_denoise(img, denoise_strength)
    img = cpl_look.apply_cpl_look(img, cpl_strength)
    img = color_grade.apply_grade(img, preset)

    target_abs = (
        storage.processing_version_path(project_id, photo_id, version_number)
        if version_number is not None
        else storage.processed_path(project_id, photo_id, preset)
    )
    target_abs.parent.mkdir(parents=True, exist_ok=True)
    tmp_abs = target_abs.with_suffix(target_abs.suffix + ".part")
    img.save(tmp_abs, format="JPEG", quality=92, optimize=True)
    tmp_abs.replace(target_abs)
    relative = storage.relative_to_storage(target_abs)
    return ProcessedPhoto(
        photo_id=photo_id,
        preset=preset,
        relative_path=relative,
        angle_applied=angle_applied,
        width=img.width,
        height=img.height,
    )


def _restore_detail_after_denoise(image: Image.Image, strength: DenoiseStrength) -> Image.Image:
    if strength is DenoiseStrength.HEAVY:
        return image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=4))
    if strength is DenoiseStrength.MEDIUM:
        return image
    return image
