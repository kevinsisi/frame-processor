"""檔案儲存：原圖落地、路徑產生、副檔名校驗。

walking skeleton 階段只處理「存原圖」與「讀檔尺寸」。處理後檔案、thumbnail 在 v0.2+ 加入。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageOps, UnidentifiedImageError

from api.config import settings

if TYPE_CHECKING:
    from fastapi import UploadFile


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tiff"}


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


def _project_originals_dir(project_id: uuid.UUID) -> Path:
    return settings.storage_root / "projects" / str(project_id) / "originals"


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


def absolute_path(relative: str) -> Path:
    return settings.storage_root / relative
