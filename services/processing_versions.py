from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from models.enums import ColorGradePreset, ProcessingJobStatus
from models.photo import Photo
from models.photo_processing_version import PhotoProcessingVersion
from models.processing_job import ProcessingJob

PHOTO_VERSION_DONE = "done"
PHOTO_VERSION_FAILED = "failed"


def update_latest_processed_cache_for_job(db: Session, job: ProcessingJob) -> None:
    if job.status is not ProcessingJobStatus.DONE or job.archived_at is not None:
        return
    rows = (
        db.execute(
            select(PhotoProcessingVersion).where(
                PhotoProcessingVersion.processing_job_id == job.id,
                PhotoProcessingVersion.status == PHOTO_VERSION_DONE,
            )
        )
        .scalars()
        .all()
    )
    if len(rows) != len(job.photo_ids or []):
        return
    for row in rows:
        if not row.path:
            continue
        photo = db.get(Photo, row.photo_id)
        if photo is None:
            continue
        paths = dict(photo.processed_paths or {})
        paths[job.preset.value] = row.path
        photo.processed_paths = paths
        flag_modified(photo, "processed_paths")


def recompute_latest_processed_cache(
    db: Session,
    *,
    project_id: UUID,
    preset: ColorGradePreset,
    photo_ids: Iterable[UUID],
) -> None:
    for photo_id in photo_ids:
        photo = db.get(Photo, photo_id)
        if photo is None:
            continue
        latest = (
            db.execute(
                select(PhotoProcessingVersion.path)
                .join(ProcessingJob, ProcessingJob.id == PhotoProcessingVersion.processing_job_id)
                .where(
                    ProcessingJob.project_id == project_id,
                    ProcessingJob.preset == preset,
                    ProcessingJob.status == ProcessingJobStatus.DONE,
                    ProcessingJob.archived_at.is_(None),
                    PhotoProcessingVersion.photo_id == photo_id,
                    PhotoProcessingVersion.status == PHOTO_VERSION_DONE,
                    PhotoProcessingVersion.path.is_not(None),
                )
                .order_by(ProcessingJob.version_number.desc())
                .limit(1)
            ).scalar_one_or_none()
        )
        paths = dict(photo.processed_paths or {})
        if latest:
            paths[preset.value] = latest
        else:
            paths.pop(preset.value, None)
        photo.processed_paths = paths
        flag_modified(photo, "processed_paths")
