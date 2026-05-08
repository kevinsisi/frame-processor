from __future__ import annotations

from typing import Any

from PIL import Image, ImageOps
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from api.config import settings
from models.adjustment_version import AdjustmentVersion
from models.photo import Photo
from models.photo_adjustment import PhotoAdjustment
from services import adjustments, storage


def source_relative_path(photo: Photo) -> str:
    paths = dict(photo.processed_paths or {})
    for key, value in paths.items():
        if key != "adjusted" and value:
            return value
    return photo.stored_path


def render_adjusted(photo: Photo, params: dict[str, Any], *, version_number: int | None = None) -> str:
    src = settings.storage_root / source_relative_path(photo)
    if not src.exists():
        raise FileNotFoundError("source image missing on disk")
    with Image.open(src) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
    img = adjustments.apply_adjustments(img, params)
    target = (
        storage.adjustment_version_path(photo.project_id, photo.id, version_number)
        if version_number is not None
        else storage.adjusted_path(photo.project_id, photo.id)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, format="JPEG", quality=92, optimize=True)
    return storage.relative_to_storage(target)


def apply_to_photo(db: Session, photo: Photo, params: dict[str, Any]) -> str:
    normalized = adjustments.normalize_params(params)
    next_version = _next_version_number(db, photo)
    relative = render_adjusted(photo, normalized, version_number=next_version)
    db.add(
        AdjustmentVersion(
            photo_id=photo.id,
            version_number=next_version,
            params=normalized,
            path=relative,
        )
    )
    adjustment = db.get(PhotoAdjustment, photo.id)
    if adjustment is None:
        adjustment = PhotoAdjustment(photo_id=photo.id, params=normalized)
        db.add(adjustment)
    else:
        adjustment.params = normalized
    paths = dict(photo.processed_paths or {})
    paths["adjusted"] = relative
    photo.processed_paths = paths
    flag_modified(photo, "processed_paths")
    return relative


def save_draft(db: Session, photo: Photo, params: dict[str, Any]) -> None:
    normalized = adjustments.normalize_params(params)
    adjustment = db.get(PhotoAdjustment, photo.id)
    if adjustment is None:
        db.add(PhotoAdjustment(photo_id=photo.id, params=normalized))
    else:
        adjustment.params = normalized


def _next_version_number(db: Session, photo: Photo) -> int:
    current = db.execute(
        select(func.max(AdjustmentVersion.version_number)).where(
            AdjustmentVersion.photo_id == photo.id
        )
    ).scalar_one_or_none()
    return int(current or 0) + 1
