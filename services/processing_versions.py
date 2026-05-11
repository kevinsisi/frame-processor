from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
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
PHOTO_VERSION_PENDING = "pending"
PHOTO_VERSION_RUNNING = "running"

_TERMINAL_PHOTO_VERSION_STATUSES = {PHOTO_VERSION_DONE, PHOTO_VERSION_FAILED}


def refresh_processing_job_progress(db: Session, job_id: UUID) -> ProcessingJob | None:
    job = db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if job is None:
        return None

    photo_ids = list(job.photo_ids or [])
    rows = (
        db.execute(
            select(PhotoProcessingVersion).where(PhotoProcessingVersion.processing_job_id == job.id)
        )
        .scalars()
        .all()
    )
    rows_by_photo = {row.photo_id: row for row in rows}
    expected_rows = [rows_by_photo.get(photo_id) for photo_id in photo_ids]
    terminal_rows = [
        row for row in expected_rows if row is not None and row.status in _TERMINAL_PHOTO_VERSION_STATUSES
    ]
    failed_rows = [row for row in terminal_rows if row.status == PHOTO_VERSION_FAILED]

    job.total = len(photo_ids)
    job.progress = len(terminal_rows)
    if not photo_ids:
        job.status = ProcessingJobStatus.FAILED
        job.error = "processing job has no photos"
        job.completed_at = datetime.now(tz=timezone.utc)
    elif len(terminal_rows) == len(photo_ids):
        job.status = ProcessingJobStatus.FAILED if failed_rows else ProcessingJobStatus.DONE
        job.error = "\n".join(row.error or str(row.photo_id) for row in failed_rows[:10]) if failed_rows else None
        job.completed_at = datetime.now(tz=timezone.utc)
        update_latest_processed_cache_for_job(db, job)
    else:
        job.status = ProcessingJobStatus.RUNNING
        job.completed_at = None
        job.error = None
    return job


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
