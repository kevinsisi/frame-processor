from __future__ import annotations

from typing import Any
from uuid import UUID

from PIL import Image, ImageOps
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from api.config import settings
from models.adjustment_version import AdjustmentVersion
from models.photo import Photo
from models.photo_adjustment import PhotoAdjustment
from models.photo_processing_version import PhotoProcessingVersion
from services import adjustments, storage


def source_relative_path(
    photo: Photo,
    source: dict[str, Any] | None = None,
    *,
    db: Session | None = None,
) -> str:
    if source:
        kind = source.get("kind")
        value = source.get("value")
        paths = dict(photo.processed_paths or {})
        if kind == "original":
            return photo.stored_path
        if kind == "preset" and value:
            relative = paths.get(str(value))
            if relative:
                return relative
            raise FileNotFoundError("selected processed version missing")
        if kind == "manual" and value:
            if db is None:
                raise FileNotFoundError("manual version lookup unavailable")
            try:
                version_id = UUID(str(value))
            except ValueError as exc:
                raise FileNotFoundError("selected manual version is invalid") from exc
            version = db.get(AdjustmentVersion, version_id)
            if version is None or version.photo_id != photo.id:
                raise FileNotFoundError("selected manual version missing")
            return version.path
        if kind == "processing" and value:
            if db is None:
                raise FileNotFoundError("AI version lookup unavailable")
            try:
                job_id = UUID(str(value))
            except ValueError as exc:
                raise FileNotFoundError("selected AI version is invalid") from exc
            version = db.execute(
                select(PhotoProcessingVersion).where(
                    PhotoProcessingVersion.processing_job_id == job_id,
                    PhotoProcessingVersion.photo_id == photo.id,
                )
            ).scalar_one_or_none()
            if version is None or version.status != "done" or not version.path:
                raise FileNotFoundError("selected AI version missing")
            return version.path

    paths = dict(photo.processed_paths or {})
    for key, value in paths.items():
        if key != "adjusted" and value:
            return value
    return photo.stored_path


def render_adjusted(
    db: Session,
    photo: Photo,
    params: dict[str, Any],
    *,
    version_number: int | None = None,
) -> str:
    src = settings.storage_root / source_relative_path(photo, params.get("source"), db=db)
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
    img.save(target, format="JPEG", quality=95, optimize=True, subsampling=0)
    return storage.relative_to_storage(target)


def apply_to_photo(db: Session, photo: Photo, params: dict[str, Any]) -> str:
    normalized = adjustments.normalize_params(params)
    if isinstance(params.get("source"), dict):
        normalized["source"] = dict(params["source"])
    next_version = _next_version_number(db, photo)
    relative = render_adjusted(db, photo, normalized, version_number=next_version)
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
    if isinstance(params.get("source"), dict):
        normalized["source"] = dict(params["source"])
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
