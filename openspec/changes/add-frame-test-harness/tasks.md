# Tasks — Backend Integration Test Harness

Status note (2026-05-16): existing tests cover pure functions and focused unit-style behavior, but the integration harness described here is still absent. There is no `tests/conftest.py`, no TestClient fixture, no testcontainers Postgres fixture, and no fake RQ queue fixture yet.

## Spec / Planning

- [ ] Confirm Option A (testcontainers Postgres 16) vs Option B/C in `design.md` with PM.
- [ ] Add `testcontainers[postgres]>=4`, `pytest-alembic>=0.11` to `pyproject.toml` optional `dev` extra.

## Harness infrastructure

- [ ] `tests/conftest.py`：session-scoped `postgres_container` fixture + module-scoped `engine` + function-scoped `db_session` with transaction rollback.
- [ ] `tests/conftest.py`：`client` fixture wiring `app.dependency_overrides[get_db]` to the test session.
- [ ] `tests/conftest.py`：`fake_queue` fixture replacing `api.queue.default_queue`; ensure `app.dependency_overrides` covers any direct queue access in routes.
- [ ] `tests/conftest.py`：factories `make_project` / `make_photo` / `make_processing_job` / `make_photo_processing_version` / `make_adjustment_version`.
- [ ] Migrate inline `_make_photo` / `_make_processing_job` in `tests/test_project_detail.py` to call the new factories.
- [ ] CLAUDE.md / README.md document the fixture pattern + how to run tests locally (Docker required).

## Port deferred batch-version-control tests

`openspec/changes/2026-05-10-batch-version-control/tasks.md § Verification (deferred)`:

- [ ] `POST /projects/{id}/process` duplicate 409 when pending/running version exists.
- [ ] `POST /projects/{id}/process` allows new version when `force=true`.
- [ ] `POST /projects/{id}/process` rejects with 400 when photo_ids contains photos from other projects.
- [ ] `POST /projects/{id}/process` returns 202 + version_number=1 for first batch, =N+1 for subsequent.
- [ ] `DELETE /processing-jobs/{id}/version` archives done/failed version, rejects running (409).
- [ ] `archived_at` archive recomputes `processed_paths` cache for affected photos.
- [ ] `recompute_latest_processed_cache` picks max(version_number) DONE non-archived version per preset.
- [ ] `update_latest_processed_cache_for_job` writes only when all photo_processing_versions in DONE status.
- [ ] `refresh_processing_job_progress` transitions to RUNNING / DONE / FAILED based on terminal photo rows.
- [ ] `refresh_processing_job_progress` returns FAILED with error string when any photo failed.
- [ ] Export with `processing_job_id`: missing-output 409 when selected version not produced for some photos.
- [ ] Export with `allow_partial=true`: emits zip of available photos, skips missing without erroring.
- [ ] Retry full flow: new version with same photo_ids, retry_scope=full, retry_of_job_id set.
- [ ] Retry-missing-only flow: new version contains only failed/missing photo subset, retry_scope=missing_only.
- [ ] Per-photo error string flows from worker into `photo_processing_versions.error` and into `_photo_out` projection.

## Worker integration

- [ ] Add `test_worker_jobs.py`: `process_photo_version_job` writes `processed/<photo>.batch-vN.jpg` immutable file.
- [ ] `process_photo_version_job` inserts/updates `photo_processing_versions` to `done` with absolute path.
- [ ] `process_photo_version_job` failure marks the row `failed` with error message, does not write the file.
- [ ] All-done photo set triggers `update_latest_processed_cache_for_job` so `Photo.processed_paths[preset]` is updated.

## Migration tests

- [ ] `pytest-alembic` round-trip: upgrade head → downgrade base → upgrade head leaves schema identical.
- [ ] `alembic 0007` migration on a DB containing pre-existing `processing_jobs` rows assigns monotonic `version_number` per project.
- [ ] `alembic 0007` upgrade then downgrade preserves data of rows that existed before the migration.

## CI wiring

- [ ] `.github/workflows/ci.yml`: install Docker buildx (or rely on default), run `pytest -q tests/`.
- [ ] CI fails when harness can't start Postgres container (don't silently skip).
- [ ] Document expected CI runtime (target < 3 minutes including container start).

## Verification

- [ ] All new tests pass locally on Windows desktop + Linux GitHub-hosted runner.
- [ ] Existing `test_adjustments_preview.py` + `test_project_detail.py` + `test_level_correct.py` still pass alongside new harness.
- [ ] `pytest -q` total runtime < 90 seconds with warm container.
- [ ] Mark `2026-05-10-batch-version-control` Verification section as fully covered and propose archive.
- [ ] Update `reference_frame_processor.md` memory: remove "Test harness 缺口" section, replace with fixture pattern summary.
- [ ] CI run on `main` shows green for new test suite.
