from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.enums import (
    AspectRatio,
    ColorGradePreset,
    DenoiseStrength,
    ExportStatus,
    ProcessingJobStatus,
)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    photo_count: int = 0


class AdjustmentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    photo_id: UUID
    version_number: int
    params: dict
    path: str
    created_at: datetime


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
    adjustment_params: dict | None = None
    adjustment_versions: list[AdjustmentVersionOut] = []


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
    denoise_strength: DenoiseStrength = DenoiseStrength.NONE
    lens_distort_correct: bool = False
    level_correct: bool = False
    auto_crop_aspect: AspectRatio | None = None
    photo_ids: list[UUID] = Field(
        default_factory=list,
        description="空 list 代表處理該 project 所有 photo",
    )


class ProcessingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: ProcessingJobStatus
    preset: ColorGradePreset
    denoise_strength: DenoiseStrength
    lens_distort_correct: bool
    level_correct: bool
    auto_crop_aspect: AspectRatio | None
    photo_ids: list[UUID]
    progress: int
    total: int
    error: str | None
    created_at: datetime
    completed_at: datetime | None
