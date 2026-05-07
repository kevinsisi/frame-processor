import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base
from models.enums import ColorGradePreset, ProcessingJobStatus


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
    preset: Mapped[ColorGradePreset] = mapped_column(
        SAEnum(ColorGradePreset, name="color_grade_preset"),
        nullable=False,
    )
    level_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_crop_aspect: Mapped[str] = mapped_column(String(16), nullable=False, default="original")
    status: Mapped[ProcessingJobStatus] = mapped_column(
        SAEnum(ProcessingJobStatus, name="processing_job_status"),
        nullable=False,
        default=ProcessingJobStatus.PENDING,
    )
    progress_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="processing_jobs")  # noqa: F821
