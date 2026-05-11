from datetime import datetime, timezone
from uuid import uuid4

from api.routers.projects import _photo_out
from api.schemas import ProcessingVersionPhotoOut
from models.adjustment_version import AdjustmentVersion
from models.photo import Photo
from models.photo_processing_version import PhotoProcessingVersion


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
