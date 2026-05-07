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
from services import auto_crop

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

    if payload.auto_crop_aspect not in auto_crop.supported_aspects():
        raise HTTPException(
            status_code=400,
            detail=f"unsupported auto_crop_aspect: {payload.auto_crop_aspect}",
        )

    if payload.photo_ids:
        photos = db.execute(
            select(Photo.id).where(
                Photo.project_id == project_id,
                Photo.id.in_(payload.photo_ids),
            )
        ).scalars().all()
        target_count = len(photos)
        if target_count != len(set(payload.photo_ids)):
            raise HTTPException(
                status_code=400, detail="some photo_ids do not belong to project"
            )
    else:
        target_count = db.execute(
            select(Photo.id).where(Photo.project_id == project_id)
        ).scalars().all()
        target_count = len(target_count)

    if target_count == 0:
        raise HTTPException(status_code=400, detail="project has no photos to process")

    job = ProcessingJob(
        project_id=project_id,
        preset=payload.preset,
        level_correct=payload.level_correct,
        auto_crop_aspect=payload.auto_crop_aspect,
        status=ProcessingJobStatus.PENDING,
        progress_total=target_count,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    photo_id_strs = [str(pid) for pid in payload.photo_ids] if payload.photo_ids else []
    default_queue.enqueue(
        "worker.jobs.processing_job",
        str(job.id),
        photo_id_strs,
        job_timeout=3600,
    )

    return ProcessingJobOut.model_validate(job)


@router.get("/processing-jobs/{job_id}", response_model=ProcessingJobOut)
def get_processing_job(
    job_id: UUID, db: Session = Depends(get_db)
) -> ProcessingJobOut:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="processing job not found")
    return ProcessingJobOut.model_validate(job)
