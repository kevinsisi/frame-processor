import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base
from models.enums import (
    AspectRatio,
    ColorGradePreset,
    DenoiseStrength,
    ProcessingJobStatus,
)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ProcessingJobStatus] = mapped_column(
        SAEnum(ProcessingJobStatus, name="processing_job_status"),
        nullable=False,
        default=ProcessingJobStatus.PENDING,
    )
    preset: Mapped[ColorGradePreset] = mapped_column(
        SAEnum(ColorGradePreset, name="color_grade_preset"),
        nullable=False,
    )
    denoise_strength: Mapped[DenoiseStrength] = mapped_column(
        SAEnum(DenoiseStrength, name="denoise_strength"),
        nullable=False,
        default=DenoiseStrength.NONE,
    )
    lens_distort_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    level_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    auto_crop_aspect: Mapped[AspectRatio | None] = mapped_column(
        SAEnum(AspectRatio, name="aspect_ratio"),
        nullable=True,
    )
    photo_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="processing_jobs")  # noqa: F821
