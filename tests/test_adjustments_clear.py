from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from api.config import settings
from models.adjustment_version import AdjustmentVersion
from models.photo import Photo
from models.photo_adjustment import PhotoAdjustment
from services import adjustment_renderer


def _build_photo(
    *,
    photo_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    processed_paths: dict[str, str] | None = None,
    with_adjustment: bool = False,
    version_paths: list[str] | None = None,
) -> Photo:
    photo_id = photo_id or uuid.uuid4()
    photo = Photo(
        id=photo_id,
        project_id=project_id or uuid.uuid4(),
        original_filename="img.jpg",
        stored_path=f"projects/{project_id}/originals/{photo_id}.jpg",
        size_bytes=1,
        width=10,
        height=10,
        mime_type="image/jpeg",
        uploaded_at=datetime.now(tz=timezone.utc),
        processed_paths=processed_paths or {},
    )
    photo.adjustment = (
        PhotoAdjustment(photo_id=photo_id, params={"contrast": 25.0})
        if with_adjustment
        else None
    )
    photo.adjustment_versions = [
        AdjustmentVersion(
            id=uuid.uuid4(),
            photo_id=photo_id,
            version_number=i + 1,
            params={"contrast": 10.0 * (i + 1)},
            path=path,
        )
        for i, path in enumerate(version_paths or [])
    ]
    return photo


def test_plan_clear_returns_none_for_photo_with_no_manual_state() -> None:
    photo = _build_photo(processed_paths={"showroom_white": "projects/x/processed/y.showroom_white.jpg"})

    plan = adjustment_renderer._plan_clear_one_photo(photo)

    assert plan is None


def test_plan_clear_collects_adjusted_cache_and_version_files() -> None:
    photo = _build_photo(
        processed_paths={
            "showroom_white": "projects/p/processed/photo.showroom_white.jpg",
            "adjusted": "projects/p/processed/photo.adjusted.jpg",
        },
        with_adjustment=True,
        version_paths=[
            "projects/p/processed/photo.manual-v1.jpg",
            "projects/p/processed/photo.manual-v2.jpg",
        ],
    )

    plan = adjustment_renderer._plan_clear_one_photo(photo)

    assert plan is not None
    assert plan.has_adjustment is True
    assert len(plan.versions) == 2
    expected_paths = {
        settings.storage_root / "projects/p/processed/photo.adjusted.jpg",
        settings.storage_root / "projects/p/processed/photo.manual-v1.jpg",
        settings.storage_root / "projects/p/processed/photo.manual-v2.jpg",
    }
    assert set(plan.paths_to_delete) == expected_paths


def test_plan_clear_removes_adjusted_cache_key_only() -> None:
    photo = _build_photo(
        processed_paths={
            "showroom_white": "projects/p/processed/photo.showroom_white.jpg",
            "adjusted": "projects/p/processed/photo.adjusted.jpg",
        },
        with_adjustment=True,
    )

    plan = adjustment_renderer._plan_clear_one_photo(photo)

    assert plan is not None
    assert plan.new_processed_paths == {
        "showroom_white": "projects/p/processed/photo.showroom_white.jpg"
    }


def test_plan_clear_handles_adjustment_only_with_no_versions_and_no_cache() -> None:
    photo = _build_photo(with_adjustment=True)

    plan = adjustment_renderer._plan_clear_one_photo(photo)

    assert plan is not None
    assert plan.has_adjustment is True
    assert plan.versions == []
    assert plan.paths_to_delete == []
    assert plan.new_processed_paths is None


def test_plan_clear_handles_versions_only_with_no_adjustment_or_cache() -> None:
    photo = _build_photo(
        version_paths=["projects/p/processed/photo.manual-v1.jpg"],
    )

    plan = adjustment_renderer._plan_clear_one_photo(photo)

    assert plan is not None
    assert plan.has_adjustment is False
    assert len(plan.versions) == 1
    assert plan.paths_to_delete == [
        settings.storage_root / "projects/p/processed/photo.manual-v1.jpg"
    ]
    assert plan.new_processed_paths is None


def test_plan_clear_handles_adjusted_cache_only() -> None:
    """A `processed_paths["adjusted"]` cache entry alone (rare, but possible after
    legacy code paths) is enough to trigger a clear so the cache key is removed."""
    photo = _build_photo(
        processed_paths={"adjusted": "projects/p/processed/photo.adjusted.jpg"},
    )

    plan = adjustment_renderer._plan_clear_one_photo(photo)

    assert plan is not None
    assert plan.has_adjustment is False
    assert plan.versions == []
    assert plan.paths_to_delete == [
        settings.storage_root / "projects/p/processed/photo.adjusted.jpg"
    ]
    assert plan.new_processed_paths == {}


def test_delete_cleared_paths_swallows_oserror_and_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    existing = tmp_path / "exists.jpg"
    existing.write_bytes(b"x")
    missing = tmp_path / "missing.jpg"

    caplog.set_level("WARNING", logger="services.adjustment_renderer")
    adjustment_renderer.delete_cleared_paths([existing, missing])

    assert not existing.exists(), "existing file should be deleted"
    # missing path simply skipped (path.exists() is False) — no warning needed.
    # No exception raised.


def test_delete_cleared_paths_logs_when_unlink_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target = tmp_path / "locked.jpg"
    target.write_bytes(b"x")

    def fail_unlink(self: Path) -> None:
        raise OSError("locked by another process")

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    caplog.set_level("WARNING", logger="services.adjustment_renderer")

    adjustment_renderer.delete_cleared_paths([target])

    assert any("locked by another process" in rec.message for rec in caplog.records)
