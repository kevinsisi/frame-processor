from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from models.enums import ColorGradePreset
from models.photo import Photo
from services import storage

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("/{photo_id}/file")
def download_photo(photo_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")
    abs_path = settings.storage_root / photo.stored_path
    if not abs_path.exists():
        raise HTTPException(status_code=410, detail="file missing on disk")
    return FileResponse(
        path=abs_path,
        media_type=photo.mime_type or "application/octet-stream",
        filename=photo.original_filename,
    )


@router.get("/{photo_id}/thumbnail")
def get_thumbnail(photo_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")
    src_abs = settings.storage_root / photo.stored_path
    if not src_abs.exists():
        raise HTTPException(status_code=410, detail="original missing on disk")
    try:
        thumb_abs = storage.ensure_thumbnail(
            project_id=photo.project_id,
            photo_id=photo.id,
            source_relative=photo.stored_path,
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"thumbnail generation failed: {exc}") from exc
    return FileResponse(path=thumb_abs, media_type="image/webp")


@router.get("/{photo_id}/processed/{preset}")
def download_processed(
    photo_id: UUID,
    preset: ColorGradePreset,
    db: Session = Depends(get_db),
) -> FileResponse:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")
    rel = photo.processed_paths.get(preset.value)
    if rel is None:
        raise HTTPException(status_code=404, detail=f"photo not yet processed with preset {preset.value}")
    abs_path = settings.storage_root / rel
    if not abs_path.exists():
        raise HTTPException(status_code=410, detail="processed file missing on disk")
    return FileResponse(
        path=abs_path,
        media_type="image/jpeg",
        filename=f"{photo.original_filename}.{preset.value}.jpg",
    )
