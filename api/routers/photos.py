from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from models.photo import Photo

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
