import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base
from models.enums import (
    AspectRatio,
    ColorGradePreset,
    CplStrength,
    DenoiseStrength,
    ProcessingJobStatus,
)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_processing_job_project_version"),
    )

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
        SAEnum(
            ProcessingJobStatus,
            name="processing_job_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        default=ProcessingJobStatus.PENDING,
    )
    preset: Mapped[ColorGradePreset] = mapped_column(
        SAEnum(
            ColorGradePreset,
            name="color_grade_preset",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
    )
    denoise_strength: Mapped[DenoiseStrength] = mapped_column(
        SAEnum(
            DenoiseStrength,
            name="denoise_strength",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        default=DenoiseStrength.NONE,
    )
    lens_distort_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    level_correct: Mapped[bool] = mapped_column(nullable=False, default=False)
    auto_crop_aspect: Mapped[AspectRatio | None] = mapped_column(
        SAEnum(
            AspectRatio,
            name="aspect_ratio",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=True,
    )
    cpl_strength: Mapped[CplStrength] = mapped_column(
        SAEnum(
            CplStrength,
            name="cpl_strength",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        default=CplStrength.NONE,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    retry_of_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True
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
    photo_versions: Mapped[list["PhotoProcessingVersion"]] = relationship(  # noqa: F821
        back_populates="processing_job", cascade="all, delete-orphan"
    )
