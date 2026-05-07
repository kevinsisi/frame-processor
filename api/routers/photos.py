from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from models.enums import ColorGradePreset
from models.photo import Photo
from services import storage

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("/{photo_id}/file")
def download_photo(
    photo_id: UUID,
    variant: Literal["original", "processed"] = Query(default="original"),
    preset: ColorGradePreset | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FileResponse:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")

    if variant == "processed":
        if preset is None:
            raise HTTPException(
                status_code=400,
                detail="preset query param required when variant=processed",
            )
        relative = (photo.processed_paths or {}).get(preset.value)
        if not relative:
            raise HTTPException(
                status_code=404,
                detail=f"no processed file for preset={preset.value}",
            )
        abs_path = settings.storage_root / relative
        media_type = "image/jpeg"
        download_name = f"{photo.id}.{preset.value}.jpg"
    else:
        abs_path = settings.storage_root / photo.stored_path
        media_type = photo.mime_type or "application/octet-stream"
        download_name = photo.original_filename

    if not abs_path.exists():
        raise HTTPException(status_code=410, detail="file missing on disk")
    return FileResponse(path=abs_path, media_type=media_type, filename=download_name)
