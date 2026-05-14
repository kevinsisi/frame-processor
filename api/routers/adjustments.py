from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.queue import default_queue
from api.schemas import PhotoOut
from models.adjustment_job import AdjustmentJob
from models.adjustment_preset import AdjustmentPreset
from models.enums import ColorGradePreset, ProcessingJobStatus
from models.photo import Photo
from models.project import Project
from services import adjustment_renderer, adjustments

router = APIRouter(tags=["adjustments"])


class AdjustmentSource(BaseModel):
    kind: Literal["auto", "original", "preset", "manual", "processing"] = "auto"
    value: str | None = None

    @model_validator(mode="after")
    def require_version_value(self) -> AdjustmentSource:
        if self.kind in {"preset", "manual", "processing"} and not (self.value or "").strip():
            raise ValueError("source value is required for preset/manual/processing sources")
        return self

    def normalized(self) -> dict[str, str | None]:
        value = self.value.strip() if isinstance(self.value, str) else None
        return {"kind": self.kind, "value": value or None}


class AdjustmentParams(BaseModel):
    exposure: float = Field(default=0, ge=-5, le=5)
    contrast: float = Field(default=0, ge=-100, le=100)
    highlights: float = Field(default=0, ge=-100, le=100)
    shadows: float = Field(default=0, ge=-100, le=100)
    temperature: float = Field(default=0, ge=-100, le=100)
    tint: float = Field(default=0, ge=-100, le=100)
    saturation: float = Field(default=0, ge=-100, le=100)
    vibrance: float = Field(default=0, ge=-100, le=100)
    clarity: float = Field(default=0, ge=-100, le=100)
    sharpness: float = Field(default=0, ge=-100, le=100)
    orientation: int = Field(default=0, ge=0, le=270)
    rotation: float = Field(default=0, ge=-45, le=45)
    crop_zoom: float = Field(default=1, ge=1, le=3)
    crop_x: float = Field(default=0, ge=-100, le=100)
    crop_y: float = Field(default=0, ge=-100, le=100)
    distortion: float = Field(default=0, ge=-100, le=100)
    distortion_x: float = Field(default=0, ge=-100, le=100)
    distortion_y: float = Field(default=0, ge=-100, le=100)
    hsl: dict[str, dict[str, float]] = Field(default_factory=dict)
    source: AdjustmentSource | None = None
    grade_preset: ColorGradePreset | None = None

    def normalized(self) -> dict[str, Any]:
        normalized = adjustments.normalize_params(self.model_dump())
        if self.source is not None:
            normalized["source"] = self.source.normalized()
        if self.grade_preset is not None:
            normalized["grade_preset"] = self.grade_preset.value
        return normalized


class AdjustmentApplyOut(BaseModel):
    photo_id: UUID
    processed_path: str
    params: dict[str, Any]


class AdjustmentBatchCreate(BaseModel):
    params: AdjustmentParams
    photo_ids: list[UUID] = Field(default_factory=list)
    sources: dict[UUID, AdjustmentSource] = Field(default_factory=dict)


class AdjustmentJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: ProcessingJobStatus
    params: dict[str, Any]
    photo_ids: list[UUID]
    progress: int
    total: int
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class AdjustmentPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    params: AdjustmentParams
    project_id: UUID | None = None


class ClearAdjustmentsRequest(BaseModel):
    photo_ids: list[UUID] = Field(default_factory=list, min_length=1)


class ClearAdjustmentsResponse(BaseModel):
    cleared_count: int
    photos: list[PhotoOut]


class AdjustmentPresetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None
    name: str
    params: dict[str, Any]
    created_at: datetime


@router.post("/photos/{photo_id}/preview")
def preview_photo_adjustment(
    photo_id: UUID,
    payload: AdjustmentParams,
    db: Session = Depends(get_db),
) -> Response:
    photo = _get_photo(db, photo_id)
    try:
        source_relative = adjustment_renderer.source_relative_path(
            photo,
            payload.source.normalized() if payload.source is not None else None,
            db=db,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    src = settings.storage_root / source_relative
    if not src.exists():
        raise HTTPException(status_code=410, detail="source image missing on disk")
    from PIL import Image, ImageOps

    with Image.open(src) as raw:
        image = ImageOps.exif_transpose(raw)
        body = adjustments.preview_jpeg(image, payload.normalized())
    return Response(content=body, media_type="image/jpeg")


@router.post("/photos/{photo_id}/adjustments", response_model=AdjustmentApplyOut)
def apply_photo_adjustment(
    photo_id: UUID,
    payload: AdjustmentParams,
    db: Session = Depends(get_db),
) -> AdjustmentApplyOut:
    photo = _get_photo(db, photo_id)
    params = payload.normalized()
    try:
        relative = adjustment_renderer.apply_to_photo(db, photo, params)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    db.commit()
    return AdjustmentApplyOut(photo_id=photo.id, processed_path=relative, params=params)


@router.put("/photos/{photo_id}/adjustments/draft", response_model=AdjustmentApplyOut)
def save_photo_adjustment_draft(
    photo_id: UUID,
    payload: AdjustmentParams,
    db: Session = Depends(get_db),
) -> AdjustmentApplyOut:
    photo = _get_photo(db, photo_id)
    params = payload.normalized()
    adjustment_renderer.save_draft(db, photo, params)
    db.commit()
    return AdjustmentApplyOut(
        photo_id=photo.id,
        processed_path=(photo.processed_paths or {}).get("adjusted", ""),
        params=params,
    )


@router.post(
    "/projects/{project_id}/adjustments/apply",
    response_model=AdjustmentJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_adjustment_job(
    project_id: UUID,
    payload: AdjustmentBatchCreate,
    db: Session = Depends(get_db),
) -> AdjustmentJobOut:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if payload.photo_ids:
        photo_ids = list(payload.photo_ids)
        existing = (
            db.execute(
                select(Photo.id).where(
                    Photo.project_id == project_id,
                    Photo.id.in_(photo_ids),
                )
            )
            .scalars()
            .all()
        )
        missing = set(photo_ids) - set(existing)
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"photos not in project: {sorted(str(m) for m in missing)}",
            )
    else:
        photo_ids = list(
            db.execute(select(Photo.id).where(Photo.project_id == project_id)).scalars().all()
        )
        if not photo_ids:
            raise HTTPException(status_code=400, detail="project has no photos")
    job_params = payload.params.normalized()
    if payload.sources:
        job_params["_sources"] = {
            str(photo_id): source.normalized()
            for photo_id, source in payload.sources.items()
        }
    job = AdjustmentJob(
        project_id=project_id,
        status=ProcessingJobStatus.PENDING,
        params=job_params,
        photo_ids=list(photo_ids),
        progress=0,
        total=len(photo_ids),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    default_queue.enqueue(
        "worker.jobs.apply_adjustments_job",
        str(job.id),
        job_timeout=settings.rq_job_timeout_adjustment_apply,
    )
    return AdjustmentJobOut.model_validate(job)


@router.post(
    "/projects/{project_id}/adjustments/clear",
    response_model=ClearAdjustmentsResponse,
)
def clear_project_adjustments(
    project_id: UUID,
    payload: ClearAdjustmentsRequest,
    db: Session = Depends(get_db),
) -> ClearAdjustmentsResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    photo_ids = list(payload.photo_ids)
    existing = (
        db.execute(
            select(Photo.id).where(
                Photo.project_id == project_id,
                Photo.id.in_(photo_ids),
            )
        )
        .scalars()
        .all()
    )
    missing = set(photo_ids) - set(existing)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"photos not in project: {sorted(str(m) for m in missing)}",
        )
    result = adjustment_renderer.clear_adjustments_for_photos(
        db, project_id=project_id, photo_ids=photo_ids
    )
    db.commit()
    for photo in result.photos:
        db.refresh(photo)
    adjustment_renderer.delete_cleared_paths(result.paths_to_delete)
    return ClearAdjustmentsResponse(
        cleared_count=result.cleared_count,
        photos=[PhotoOut.model_validate(p) for p in result.photos],
    )


@router.get("/adjustment-jobs/{job_id}", response_model=AdjustmentJobOut)
def get_adjustment_job(job_id: UUID, db: Session = Depends(get_db)) -> AdjustmentJobOut:
    job = db.get(AdjustmentJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="adjustment job not found")
    return AdjustmentJobOut.model_validate(job)


@router.post(
    "/adjustment-presets",
    response_model=AdjustmentPresetOut,
    status_code=status.HTTP_201_CREATED,
)
def create_adjustment_preset(
    payload: AdjustmentPresetCreate,
    db: Session = Depends(get_db),
) -> AdjustmentPresetOut:
    if payload.project_id is not None and db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    preset = AdjustmentPreset(
        project_id=payload.project_id,
        name=payload.name.strip(),
        params=payload.params.normalized(),
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return AdjustmentPresetOut.model_validate(preset)


@router.get("/adjustment-presets", response_model=list[AdjustmentPresetOut])
def list_adjustment_presets(
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> list[AdjustmentPresetOut]:
    stmt = select(AdjustmentPreset).order_by(AdjustmentPreset.created_at.desc())
    if project_id is not None:
        stmt = stmt.where(
            (AdjustmentPreset.project_id.is_(None))
            | (AdjustmentPreset.project_id == project_id)
        )
    presets = db.execute(stmt).scalars().all()
    return [AdjustmentPresetOut.model_validate(preset) for preset in presets]


@router.delete("/adjustment-presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_adjustment_preset(
    preset_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    preset = db.get(AdjustmentPreset, preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="preset not found")
    db.delete(preset)
    db.commit()


def _get_photo(db: Session, photo_id: UUID) -> Photo:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")
    return photo
