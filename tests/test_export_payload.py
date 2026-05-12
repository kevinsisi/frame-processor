from types import SimpleNamespace
from uuid import uuid4

from worker.jobs import _legacy_export_payload, _pick_export_path


class _FakeResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def tuples(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, results) -> None:
        self._results = list(results)
        self.statements: list[str] = []

    def execute(self, statement):
        self.statements.append(str(statement))
        return _FakeResult(self._results.pop(0))


def test_pick_export_path_prefers_adjusted_over_latest_ai_version() -> None:
    assert (
        _pick_export_path(
            "projects/p/originals/sample.jpg",
            {"adjusted": "projects/p/processed/sample.manual-v1.jpg"},
            "projects/p/processed/sample.batch-v3.jpg",
        )
        == "projects/p/processed/sample.manual-v1.jpg"
    )


def test_pick_export_path_uses_latest_ai_version_when_cache_is_empty() -> None:
    assert (
        _pick_export_path(
            "projects/p/originals/sample.jpg",
            {},
            "projects/p/processed/sample.batch-v3.jpg",
        )
        == "projects/p/processed/sample.batch-v3.jpg"
    )


def test_pick_export_path_falls_back_to_cached_processed_then_original() -> None:
    assert (
        _pick_export_path(
            "projects/p/originals/sample.jpg",
            {"showroom_white": "projects/p/processed/sample.showroom.jpg"},
        )
        == "projects/p/processed/sample.showroom.jpg"
    )
    assert _pick_export_path("projects/p/originals/sample.jpg", {}) == "projects/p/originals/sample.jpg"


def test_legacy_export_payload_uses_latest_done_ai_version_when_cache_is_empty() -> None:
    project_id = uuid4()
    photo_id = uuid4()
    db = _FakeDb(
        [
            [(photo_id, "sample.jpg", "projects/p/originals/sample.jpg", {})],
            [(photo_id, "projects/p/processed/sample.batch-v3.jpg")],
        ]
    )

    payload = _legacy_export_payload(db, SimpleNamespace(project_id=project_id))

    assert payload == [("sample.jpg", "projects/p/processed/sample.batch-v3.jpg")]
    latest_query = db.statements[1]
    assert "processing_jobs" in latest_query
    assert "photo_processing_versions" in latest_query
    assert "processing_jobs.status" in latest_query
    assert "processing_jobs.archived_at IS NULL" in latest_query
    assert "ORDER BY processing_jobs.version_number DESC" in latest_query
