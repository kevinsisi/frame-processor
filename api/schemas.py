from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ColorGradePreset, ExportStatus, ProcessingJobStatus


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
    processed_paths: dict[str, str] = {}


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


class ProcessingJobCreate(BaseModel):
    preset: ColorGradePreset
    photo_ids: list[UUID] = []
    level_correct: bool = True
    auto_crop_aspect: str = "original"


class ProcessingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    preset: ColorGradePreset
    level_correct: bool
    auto_crop_aspect: str
    status: ProcessingJobStatus
    progress_done: int
    progress_total: int
    error: str | None
    created_at: datetime
    completed_at: datetime | None
