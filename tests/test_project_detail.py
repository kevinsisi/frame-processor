from datetime import datetime, timezone
from uuid import uuid4

from api.routers.projects import _photo_out, _processing_version_out
from api.schemas import ProcessingVersionPhotoOut
from models.adjustment_version import AdjustmentVersion
from models.enums import (
    AspectRatio,
    ChromaCleanStrength,
    ColorGradePreset,
    CplStrength,
    DenoiseStrength,
    DetailPreserveStrength,
    ProcessingJobStatus,
)
from models.photo import Photo
from models.photo_processing_version import PhotoProcessingVersion
from models.processing_job import ProcessingJob


def test_photo_out_ignores_raw_processing_relationship_without_version_number() -> None:
    photo_id = uuid4()
    job_id = uuid4()
    photo = Photo(
        id=photo_id,
        project_id=uuid4(),
        original_filename="sample.jpg",
        stored_path="projects/p/originals/sample.jpg",
        size_bytes=123,
        width=100,
        height=80,
        mime_type="image/jpeg",
        uploaded_at=datetime.now(tz=timezone.utc),
        processed_paths={},
    )
    photo.processing_versions = [
        PhotoProcessingVersion(
            processing_job_id=job_id,
            photo_id=photo_id,
            status="done",
            path="projects/p/processed/sample.batch-v1.jpg",
        )
    ]

    result = _photo_out(
        photo,
        {
            photo_id: [
                ProcessingVersionPhotoOut(
                    processing_job_id=job_id,
                    version_number=1,
                    status="done",
                    path="projects/p/processed/sample.batch-v1.jpg",
                    error=None,
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        },
    )

    assert result.processing_versions[0].version_number == 1
    assert result.adjustment_versions == []


def test_photo_out_serializes_manual_adjustment_versions() -> None:
    photo_id = uuid4()
    photo = Photo(
        id=photo_id,
        project_id=uuid4(),
        original_filename="manual.jpg",
        stored_path="projects/p/originals/manual.jpg",
        size_bytes=123,
        width=100,
        height=80,
        mime_type="image/jpeg",
        uploaded_at=datetime.now(tz=timezone.utc),
        processed_paths={},
    )
    photo.adjustment_versions = [
        AdjustmentVersion(
            id=uuid4(),
            photo_id=photo_id,
            version_number=2,
            params={"exposure": 1},
            path="projects/p/processed/manual.manual-v2.jpg",
            created_at=datetime.now(tz=timezone.utc),
        )
    ]

    result = _photo_out(photo, {})

    assert result.adjustment_versions[0].version_number == 2
    assert result.adjustment_versions[0].params == {"exposure": 1}
    assert result.adjustment_versions[0].path == "projects/p/processed/manual.manual-v2.jpg"
    assert result.processing_versions == []


def _make_photo(photo_id=None) -> Photo:
    return Photo(
        id=photo_id or uuid4(),
        project_id=uuid4(),
        original_filename="sample.jpg",
        stored_path="projects/p/originals/sample.jpg",
        size_bytes=123,
        width=100,
        height=80,
        mime_type="image/jpeg",
        uploaded_at=datetime.now(tz=timezone.utc),
        processed_paths={},
    )


def test_photo_out_passes_through_failed_version_error() -> None:
    photo = _make_photo()
    result = _photo_out(
        photo,
        {
            photo.id: [
                ProcessingVersionPhotoOut(
                    processing_job_id=uuid4(),
                    version_number=3,
                    status="failed",
                    path=None,
                    error="worker oom",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        },
    )

    assert len(result.processing_versions) == 1
    projected = result.processing_versions[0]
    assert projected.status == "failed"
    assert projected.path is None
    assert projected.error == "worker oom"
    assert projected.version_number == 3


def test_photo_out_preserves_processing_version_order() -> None:
    photo = _make_photo()
    job_a, job_b = uuid4(), uuid4()
    created_at = datetime.now(tz=timezone.utc)
    result = _photo_out(
        photo,
        {
            photo.id: [
                ProcessingVersionPhotoOut(
                    processing_job_id=job_a,
                    version_number=2,
                    status="done",
                    path="projects/p/processed/sample.batch-v2.jpg",
                    error=None,
                    created_at=created_at,
                ),
                ProcessingVersionPhotoOut(
                    processing_job_id=job_b,
                    version_number=1,
                    status="done",
                    path="projects/p/processed/sample.batch-v1.jpg",
                    error=None,
                    created_at=created_at,
                ),
            ]
        },
    )

    assert [v.version_number for v in result.processing_versions] == [2, 1]
    assert result.processing_versions[0].processing_job_id == job_a


def test_photo_out_combines_processing_and_adjustment_versions() -> None:
    photo = _make_photo()
    photo.adjustment_versions = [
        AdjustmentVersion(
            id=uuid4(),
            photo_id=photo.id,
            version_number=1,
            params={"contrast": 0.2},
            path="projects/p/processed/sample.manual-v1.jpg",
            created_at=datetime.now(tz=timezone.utc),
        )
    ]
    result = _photo_out(
        photo,
        {
            photo.id: [
                ProcessingVersionPhotoOut(
                    processing_job_id=uuid4(),
                    version_number=1,
                    status="done",
                    path="projects/p/processed/sample.batch-v1.jpg",
                    error=None,
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        },
    )

    assert len(result.processing_versions) == 1
    assert len(result.adjustment_versions) == 1
    assert result.adjustment_versions[0].params == {"contrast": 0.2}


def _make_processing_job(**overrides) -> ProcessingJob:
    fields = {
        "id": uuid4(),
        "project_id": uuid4(),
        "status": ProcessingJobStatus.DONE,
        "preset": ColorGradePreset.SHOWROOM_WHITE,
        "denoise_strength": DenoiseStrength.MEDIUM,
        "lens_distort_correct": True,
        "level_correct": True,
        "auto_crop_aspect": AspectRatio.ORIGINAL,
        "cpl_strength": CplStrength.NONE,
        "chroma_clean_strength": ChromaCleanStrength.MEDIUM,
        "detail_preserve_strength": DetailPreserveStrength.LOW,
        "version_number": 1,
        "photo_ids": [uuid4()],
        "progress": 1,
        "total": 1,
        "retry_scope": "none",
        "retry_of_job_id": None,
        "created_at": datetime.now(tz=timezone.utc),
        "completed_at": datetime.now(tz=timezone.utc),
        "error": None,
    }
    fields.update(overrides)
    return ProcessingJob(**fields)


def test_processing_version_out_maps_all_settings() -> None:
    job = _make_processing_job()
    out = _processing_version_out(job)

    assert out.id == job.id
    assert out.project_id == job.project_id
    assert out.version_number == 1
    assert out.status == ProcessingJobStatus.DONE
    assert out.preset == ColorGradePreset.SHOWROOM_WHITE
    assert out.denoise_strength == DenoiseStrength.MEDIUM
    assert out.lens_distort_correct is True
    assert out.level_correct is True
    assert out.auto_crop_aspect == AspectRatio.ORIGINAL
    assert out.chroma_clean_strength == ChromaCleanStrength.MEDIUM
    assert out.detail_preserve_strength == DetailPreserveStrength.LOW
    assert out.cpl_strength == CplStrength.NONE
    assert out.photo_ids == job.photo_ids
    assert out.error is None
    assert out.retry_scope == "none"
    assert out.retry_of_job_id is None
    assert out.completed_at is not None


def test_processing_version_out_projects_failed_version_error() -> None:
    job = _make_processing_job(
        status=ProcessingJobStatus.FAILED,
        error="batch failed: 2/3 photos failed",
        progress=2,
        total=3,
        completed_at=datetime.now(tz=timezone.utc),
    )
    out = _processing_version_out(job)

    assert out.status == ProcessingJobStatus.FAILED
    assert out.error == "batch failed: 2/3 photos failed"
    assert out.progress == 2
    assert out.total == 3


def test_processing_version_out_projects_retry_metadata() -> None:
    parent_id = uuid4()
    job = _make_processing_job(
        retry_scope="missing_only",
        retry_of_job_id=parent_id,
        version_number=2,
    )
    out = _processing_version_out(job)

    assert out.retry_scope == "missing_only"
    assert out.retry_of_job_id == parent_id
    assert out.version_number == 2


def test_processing_version_out_handles_pending_job_without_completion() -> None:
    job = _make_processing_job(
        status=ProcessingJobStatus.PENDING,
        progress=0,
        total=3,
        photo_ids=[uuid4(), uuid4(), uuid4()],
        completed_at=None,
    )
    out = _processing_version_out(job)

    assert out.status == ProcessingJobStatus.PENDING
    assert out.completed_at is None
    assert out.progress == 0
    assert out.total == 3
