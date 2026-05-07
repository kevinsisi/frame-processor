"""檔案儲存：原圖落地、處理後路徑、thumbnail lazy generation。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageOps, UnidentifiedImageError

from api.config import settings
from models.enums import ColorGradePreset

if TYPE_CHECKING:
    from fastapi import UploadFile


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tiff"}

THUMBNAIL_LONG_EDGE = 600
PROCESSED_JPEG_QUALITY = 92


class UnsupportedFormatError(ValueError):
    pass


@dataclass(slots=True)
class StoredPhoto:
    photo_id: uuid.UUID
    original_filename: str
    relative_path: Path
    absolute_path: Path
    size_bytes: int
    width: int | None
    height: int | None
    mime_type: str | None


def _project_dir(project_id: uuid.UUID) -> Path:
    return settings.storage_root / "projects" / str(project_id)


def _project_originals_dir(project_id: uuid.UUID) -> Path:
    return _project_dir(project_id) / "originals"


def _project_processed_dir(project_id: uuid.UUID) -> Path:
    return _project_dir(project_id) / "processed"


def _project_thumbnails_dir(project_id: uuid.UUID) -> Path:
    return _project_dir(project_id) / "thumbnails"


def _ext_from_filename(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(f"unsupported extension: {suffix or '(none)'}")
    return suffix


def save_original(*, project_id: uuid.UUID, upload: UploadFile) -> StoredPhoto:
    """把上傳的單張照片寫入原圖目錄，回傳檔案 metadata。"""

    original_filename = upload.filename or "unnamed"
    ext = _ext_from_filename(original_filename)

    photo_id = uuid.uuid4()
    target_dir = _project_originals_dir(project_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_abs = target_dir / f"{photo_id}{ext}"

    contents = upload.file.read()
    target_abs.write_bytes(contents)

    width, height = _read_dimensions(target_abs)

    relative = target_abs.relative_to(settings.storage_root)
    return StoredPhoto(
        photo_id=photo_id,
        original_filename=original_filename,
        relative_path=relative,
        absolute_path=target_abs,
        size_bytes=len(contents),
        width=width,
        height=height,
        mime_type=upload.content_type,
    )


def _read_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            return img.width, img.height
    except (UnidentifiedImageError, OSError):
        return None, None


def absolute_path(relative: str | Path) -> Path:
    return settings.storage_root / relative


def processed_relative_path(
    *,
    project_id: uuid.UUID,
    photo_id: uuid.UUID,
    preset: ColorGradePreset,
) -> Path:
    return Path("projects") / str(project_id) / "processed" / f"{photo_id}.{preset.value}.jpg"


def processed_absolute_path(
    *,
    project_id: uuid.UUID,
    photo_id: uuid.UUID,
    preset: ColorGradePreset,
) -> Path:
    rel = processed_relative_path(project_id=project_id, photo_id=photo_id, preset=preset)
    abs_path = settings.storage_root / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    return abs_path


def thumbnail_relative_path(*, project_id: uuid.UUID, photo_id: uuid.UUID) -> Path:
    return Path("projects") / str(project_id) / "thumbnails" / f"{photo_id}.webp"


def thumbnail_absolute_path(*, project_id: uuid.UUID, photo_id: uuid.UUID) -> Path:
    rel = thumbnail_relative_path(project_id=project_id, photo_id=photo_id)
    abs_path = settings.storage_root / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    return abs_path


def ensure_thumbnail(*, project_id: uuid.UUID, photo_id: uuid.UUID, source_relative: str | Path) -> Path:
    """產 long-edge 600px webp thumbnail；已存在就直接回傳路徑（lazy cache）。"""

    abs_path = thumbnail_absolute_path(project_id=project_id, photo_id=photo_id)
    if abs_path.exists() and abs_path.stat().st_size > 0:
        return abs_path

    src_abs = absolute_path(source_relative)
    with Image.open(src_abs) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((THUMBNAIL_LONG_EDGE, THUMBNAIL_LONG_EDGE), Image.LANCZOS)
        img.convert("RGB").save(abs_path, format="WEBP", quality=82, method=4)
    return abs_path


def save_processed_jpeg(image: Image.Image, abs_path: Path) -> int:
    """寫處理後 JPEG（quality=92）。回傳檔案大小。"""

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(abs_path, format="JPEG", quality=PROCESSED_JPEG_QUALITY, optimize=True)
    return abs_path.stat().st_size
