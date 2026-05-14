from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.queue import default_queue
from api.schemas import ExportCreate, ExportOut
from models.enums import ExportStatus
from models.export import Export
from models.photo import Photo
from models.photo_processing_version import PhotoProcessingVersion
from models.processing_job import ProcessingJob
from models.project import Project
from services.processing_versions import PHOTO_VERSION_DONE

router = APIRouter(tags=["exports"])


def _validate_processing_version_export(
    db: Session,
    job: ProcessingJob,
    *,
    allow_partial: bool,
) -> None:
    photos = (
        db.execute(
            select(Photo.id, Photo.original_filename)
            .where(Photo.project_id == job.project_id, Photo.id.in_(job.photo_ids or []))
            .order_by(Photo.uploaded_at)
        )
        .tuples()
        .all()
    )
    rows = (
        db.execute(
            select(
                PhotoProcessingVersion.photo_id,
                PhotoProcessingVersion.path,
                PhotoProcessingVersion.status,
            ).where(PhotoProcessingVersion.processing_job_id == job.id)
        )
        .tuples()
        .all()
    )
    rows_by_photo = {photo_id: (path, row_status) for photo_id, path, row_status in rows}
    missing: list[str] = []
    successful = 0
    for photo_id, original_name in photos:
        path, row_status = rows_by_photo.get(photo_id, (None, None))
        if row_status == PHOTO_VERSION_DONE and path:
            successful += 1
        else:
            missing.append(original_name)
    if missing and not allow_partial:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="selected AI version is missing outputs: " + ", ".join(missing[:10]),
        )
    if successful == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="selected AI version has no successful outputs",
        )


@router.post(
    "/projects/{project_id}/exports",
    response_model=ExportOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_export(
    project_id: UUID,
    payload: ExportCreate | None = None,
    db: Session = Depends(get_db),
) -> ExportOut:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    payload = payload or ExportCreate()
    if payload.processing_job_id is not None:
        job = db.get(ProcessingJob, payload.processing_job_id)
        if job is None or job.project_id != project_id:
            raise HTTPException(status_code=404, detail="AI version not found")
        if job.archived_at is not None:
            raise HTTPException(status_code=410, detail="AI version is archived")
        _validate_processing_version_export(db, job, allow_partial=payload.allow_partial)

    export = Export(
        project_id=project_id,
        processing_job_id=payload.processing_job_id,
        allow_partial=payload.allow_partial,
        status=ExportStatus.PENDING,
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    default_queue.enqueue(
        "worker.jobs.zip_export_job",
        str(export.id),
        job_timeout=settings.rq_job_timeout_zip_export,
    )

    return ExportOut.model_validate(export)


@router.get("/exports/{export_id}", response_model=ExportOut)
def get_export(export_id: UUID, db: Session = Depends(get_db)) -> ExportOut:
    export = db.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="export not found")
    return ExportOut.model_validate(export)


@router.get("/exports/{export_id}/download")
def download_export(export_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    export = db.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="export not found")
    if export.status != ExportStatus.DONE or export.zip_path is None:
        raise HTTPException(status_code=409, detail=f"export not ready (status={export.status.value})")
    abs_path = settings.storage_root / export.zip_path
    if not abs_path.exists():
        raise HTTPException(status_code=410, detail="zip missing on disk")
    return FileResponse(
        path=abs_path,
        media_type="application/zip",
        filename=f"frame-processor-{export.project_id}-{export.id}.zip",
    )
