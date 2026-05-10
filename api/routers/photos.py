from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from models.adjustment_version import AdjustmentVersion
from models.enums import ColorGradePreset
from models.photo import Photo
from models.photo_processing_version import PhotoProcessingVersion
from models.processing_job import ProcessingJob

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("/{photo_id}/file")
def download_photo(
    photo_id: UUID,
    variant: Literal["original", "processed"] = Query(default="original"),
    preset: ColorGradePreset | Literal["adjusted"] | None = Query(default=None),
    version_id: UUID | None = Query(default=None),
    processing_job_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FileResponse:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")

    if processing_job_id is not None:
        job = db.get(ProcessingJob, processing_job_id)
        if job is None or job.project_id != photo.project_id or job.archived_at is not None:
            raise HTTPException(status_code=404, detail="AI version not found")
        version = (
            db.query(PhotoProcessingVersion)
            .filter(
                PhotoProcessingVersion.processing_job_id == processing_job_id,
                PhotoProcessingVersion.photo_id == photo.id,
            )
            .one_or_none()
        )
        if version is None or version.status != "done" or not version.path:
            raise HTTPException(status_code=404, detail="photo has no output in selected AI version")
        abs_path = settings.storage_root / version.path
        media_type = "image/jpeg"
        stem = photo.original_filename.rsplit(".", 1)[0]
        download_name = f"{stem}.ai-v{job.version_number}.jpg"
    elif version_id is not None:
        version = db.get(AdjustmentVersion, version_id)
        if version is None or version.photo_id != photo.id:
            raise HTTPException(status_code=404, detail="adjustment version not found")
        abs_path = settings.storage_root / version.path
        media_type = "image/jpeg"
        stem = photo.original_filename.rsplit(".", 1)[0]
        download_name = f"{stem}.manual-v{version.version_number}.jpg"
    elif variant == "processed":
        if preset is None:
            raise HTTPException(
                status_code=400,
                detail="preset query param required when variant=processed",
            )
        preset_key = preset.value if isinstance(preset, ColorGradePreset) else preset
        relative = (photo.processed_paths or {}).get(preset_key)
        if not relative:
            raise HTTPException(
                status_code=404,
                detail=f"no processed file for preset={preset_key}",
            )
        abs_path = settings.storage_root / relative
        media_type = "image/jpeg"
        download_name = f"{photo.id}.{preset_key}.jpg"
    else:
        abs_path = settings.storage_root / photo.stored_path
        media_type = photo.mime_type or "application/octet-stream"
        download_name = photo.original_filename

    if not abs_path.exists():
        raise HTTPException(status_code=410, detail="file missing on disk")
    return FileResponse(path=abs_path, media_type=media_type, filename=download_name)
