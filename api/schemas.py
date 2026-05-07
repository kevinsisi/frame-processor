from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ExportStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    photo_count: int = 0


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    original_filename: str
    size_bytes: int
    width: int | None
    height: int | None
    mime_type: str | None
    uploaded_at: datetime


class ProjectDetail(ProjectOut):
    photos: list[PhotoOut] = []


class ExportCreate(BaseModel):
    pass


class ExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: ExportStatus
    error: str | None
    created_at: datetime
    completed_at: datetime | None
