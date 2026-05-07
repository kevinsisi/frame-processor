from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.queue import default_queue
from api.schemas import ProcessingJobCreate, ProcessingJobOut
from models.enums import ProcessingJobStatus
from models.photo import Photo
from models.processing_job import ProcessingJob
from models.project import Project

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

    job = ProcessingJob(
        project_id=project_id,
        status=ProcessingJobStatus.PENDING,
        preset=payload.preset,
        denoise_strength=payload.denoise_strength,
        lens_distort_correct=payload.lens_distort_correct,
        level_correct=payload.level_correct,
        auto_crop_aspect=payload.auto_crop_aspect,
        photo_ids=list(photo_ids),
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
