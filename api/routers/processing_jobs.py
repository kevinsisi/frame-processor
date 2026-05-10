from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.queue import default_queue
from api.schemas import ProcessingJobCreate, ProcessingJobOut
from models.enums import ProcessingJobStatus
from models.photo import Photo
from models.processing_job import ProcessingJob
from models.project import Project
from services.processing_versions import recompute_latest_processed_cache

router = APIRouter(tags=["processing"])


@router.post(
    "/projects/{project_id}/process",
    response_model=ProcessingJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_processing_job(
    project_id: UUID,
    payload: ProcessingJobCreate,
    db: Session = Depends(get_db),
) -> ProcessingJobOut:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    in_flight = db.execute(
        select(ProcessingJob.id).where(
            ProcessingJob.project_id == project_id,
            ProcessingJob.archived_at.is_(None),
            ProcessingJob.status.in_([ProcessingJobStatus.PENDING, ProcessingJobStatus.RUNNING]),
        )
    ).first()
    if in_flight is not None and not payload.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="another AI batch version is already running for this project",
        )

    if payload.retry_of_job_id is not None:
        source_job = db.get(ProcessingJob, payload.retry_of_job_id)
        if source_job is None or source_job.project_id != project_id:
            raise HTTPException(status_code=404, detail="retry source version not found")

    if payload.photo_ids:
        photo_ids = list(payload.photo_ids)
        existing = (
            db.execute(
                select(Photo.id).where(
                    Photo.project_id == project_id, Photo.id.in_(photo_ids)
                )
            )
            .scalars()
            .all()
        )
        missing = set(photo_ids) - set(existing)
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"photos not in project: {sorted(str(m) for m in missing)}",
            )
    else:
        photo_ids = (
            db.execute(select(Photo.id).where(Photo.project_id == project_id))
            .scalars()
            .all()
        )
        if not photo_ids:
            raise HTTPException(status_code=400, detail="project has no photos")

    next_version = int(
        db.execute(
            select(func.max(ProcessingJob.version_number)).where(ProcessingJob.project_id == project_id)
        ).scalar_one_or_none()
        or 0
    ) + 1

    job = ProcessingJob(
        project_id=project_id,
        status=ProcessingJobStatus.PENDING,
        version_number=next_version,
        preset=payload.preset,
        denoise_strength=payload.denoise_strength,
        lens_distort_correct=payload.lens_distort_correct,
        level_correct=payload.level_correct,
        auto_crop_aspect=payload.auto_crop_aspect,
        photo_ids=list(photo_ids),
        retry_scope=payload.retry_scope,
        retry_of_job_id=payload.retry_of_job_id,
        progress=0,
        total=len(photo_ids),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    default_queue.enqueue(
        "worker.jobs.process_photos_job", str(job.id), job_timeout=1800
    )
    return ProcessingJobOut.model_validate(job)


@router.get("/processing-jobs/{job_id}", response_model=ProcessingJobOut)
def get_processing_job(job_id: UUID, db: Session = Depends(get_db)) -> ProcessingJobOut:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="processing job not found")
    return ProcessingJobOut.model_validate(job)


@router.delete("/processing-jobs/{job_id}/version", response_model=ProcessingJobOut)
def archive_processing_version(job_id: UUID, db: Session = Depends(get_db)) -> ProcessingJobOut:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="processing job not found")
    if job.status in (ProcessingJobStatus.PENDING, ProcessingJobStatus.RUNNING):
        raise HTTPException(status_code=409, detail="cannot archive a running AI version")
    if job.archived_at is None:
        job.archived_at = datetime.now(tz=timezone.utc)
        recompute_latest_processed_cache(
            db,
            project_id=job.project_id,
            preset=job.preset,
            photo_ids=job.photo_ids or [],
        )
        db.commit()
        db.refresh(job)
    return ProcessingJobOut.model_validate(job)
