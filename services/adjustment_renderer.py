from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
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

logger = logging.getLogger(__name__)


@dataclass
class ClearAdjustmentsResult:
    cleared_count: int = 0
    photos: list[Photo] = field(default_factory=list)
    paths_to_delete: list[Path] = field(default_factory=list)


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


def clear_adjustments_for_photos(
    db: Session,
    *,
    project_id: UUID,
    photo_ids: Iterable[UUID],
) -> ClearAdjustmentsResult:
    """Hard-delete manual adjustment state for each photo and collect disk paths to delete.

    Per photo: deletes `PhotoAdjustment` draft + every `AdjustmentVersion` row +
    clears `processed_paths["adjusted"]` cache entry. Photos with no manual
    adjustment state are silently skipped (no-op, not counted). Disk file deletes
    are returned as `paths_to_delete` for the caller to execute post-commit.
    """
    result = ClearAdjustmentsResult()
    for photo_id in photo_ids:
        photo = db.get(Photo, photo_id)
        if photo is None or photo.project_id != project_id:
            continue
        if _clear_photo_adjustments(db, photo, result.paths_to_delete):
            result.cleared_count += 1
            result.photos.append(photo)
    return result


@dataclass
class _ClearPlan:
    """Per-photo plan describing what clear_adjustments_for_photos will mutate.

    Separated from session mutation so tests can drive plan computation against
    plain Photo objects without a DB session.
    """

    has_adjustment: bool
    versions: list[AdjustmentVersion]
    paths_to_delete: list[Path]
    new_processed_paths: dict[str, str] | None


def _plan_clear_one_photo(photo: Photo) -> _ClearPlan | None:
    versions = list(photo.adjustment_versions)
    adjusted_cache_path = (photo.processed_paths or {}).get("adjusted")
    has_adjustment = photo.adjustment is not None
    if not has_adjustment and not versions and not adjusted_cache_path:
        return None

    paths_to_delete: list[Path] = []
    if adjusted_cache_path:
        paths_to_delete.append(settings.storage_root / adjusted_cache_path)
    for version in versions:
        if version.path:
            paths_to_delete.append(settings.storage_root / version.path)

    new_paths: dict[str, str] | None = None
    existing_paths = dict(photo.processed_paths or {})
    if "adjusted" in existing_paths:
        del existing_paths["adjusted"]
        new_paths = existing_paths

    return _ClearPlan(
        has_adjustment=has_adjustment,
        versions=versions,
        paths_to_delete=paths_to_delete,
        new_processed_paths=new_paths,
    )


def _clear_photo_adjustments(
    db: Session, photo: Photo, paths_to_delete: list[Path]
) -> bool:
    """Mutate session to clear one photo's manual adjustment state.

    Returns True if anything was cleared, False if the photo had no manual state.
    """
    plan = _plan_clear_one_photo(photo)
    if plan is None:
        return False

    if plan.has_adjustment and photo.adjustment is not None:
        db.delete(photo.adjustment)
    for version in plan.versions:
        db.delete(version)
    if plan.new_processed_paths is not None:
        photo.processed_paths = plan.new_processed_paths
        flag_modified(photo, "processed_paths")

    paths_to_delete.extend(plan.paths_to_delete)
    return True


def delete_cleared_paths(paths: Iterable[Path]) -> None:
    """Best-effort post-commit disk delete. Log on failure, do not raise."""
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            logger.warning("failed to delete manual version file %s: %s", path, exc)
