from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.queue import default_queue
from api.schemas import ExportOut
from models.enums import ExportStatus
from models.export import Export
from models.project import Project

router = APIRouter(tags=["exports"])


@router.post(
    "/projects/{project_id}/exports",
    response_model=ExportOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_export(project_id: UUID, db: Session = Depends(get_db)) -> ExportOut:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    export = Export(project_id=project_id, status=ExportStatus.PENDING)
    db.add(export)
    db.commit()
    db.refresh(export)

    default_queue.enqueue("worker.jobs.zip_export_job", str(export.id), job_timeout=600)

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
