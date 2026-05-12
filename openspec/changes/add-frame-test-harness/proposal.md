# Proposal: Backend Integration Test Harness

## Summary

Build the missing integration test harness for the FastAPI + SQLAlchemy + RQ stack so backend tests can exercise real DB writes, API routes, and worker enqueue behavior. Currently `tests/` is pure-function only — projection helpers and pipeline image transforms — which has left the deferred verification items in `2026-05-10-batch-version-control` un-runnable and `2026-05-07-v0.3.0-adjustment-panel`'s mobile / smoke checklist hand-driven.

## Motivation

- `2026-05-10-batch-version-control` shipped feature-complete but its Verification section is explicitly marked **Deferred — needs integration test harness**: duplicate-blocking 409, `force=true`, archive 409 on running version, selected-version export missing-output 409, partial export, `processed_paths` cache recomputation, `refresh_processing_job_progress` terminal-status math, alembic 0007 initial version numbering, file/DB consistency cleanup. All of these are exact regressions that the existing pure-function tests cannot catch.
- Worker-side logic (`worker.jobs.process_photo_version_job` writing `batch-vN` immutable paths and inserting per-photo version rows) has no automated coverage at all.
- Without a TestClient fixture, every refactor touching API contracts has to be smoke-tested by hand in Preview / Export — that is the ground truth for why iPhone Safari and showroom_white smoke items in v0.3.0 keep slipping.
- The repo deliberately picked PostgreSQL + JSONB + Postgres-specific enums + ARRAY columns, which means a trivial `sqlite:///:memory:` swap will not work; the harness needs a deliberate decision.

## Scope

- Pick one of: (a) testcontainers Postgres 16 fixture; (b) sqlite shim + JSONB → JSON + Postgres-enum → CHECK shim for the subset of models we need; (c) a real Postgres DB started by `pytest-docker` or `docker compose`. Design tradeoffs in `design.md`.
- Add `tests/conftest.py` with at least: `db_session` (per-test transaction rollback), `client` (FastAPI TestClient bound to that session), `fake_queue` (in-memory RQ-compatible queue that records `enqueue` calls without running the worker), `make_project`/`make_photo`/`make_processing_job` factories.
- Promote existing inline helpers in `tests/test_project_detail.py` (`_make_photo`, `_make_processing_job`) into the conftest factories.
- Port every deferred Verification item from `2026-05-10-batch-version-control/tasks.md` into integration tests.
- Add smoke tests for `worker.jobs.process_photo_version_job` using a tiny synthetic image — verify it writes `batch-vN.jpg`, inserts the `photo_processing_versions` row with `done`, and updates `processed_paths` cache.
- Wire the new harness into `.github/workflows/ci.yml` so CI runs `pytest -q` with the chosen DB backend.
- Update `tests/`-using docs (`CLAUDE.md` test section, `README.md` 本機開發 section) to describe the new fixture pattern.

## Non-Goals

- Not building a full end-to-end browser harness (Playwright/Cypress). Frontend regression remains manual until UX stabilizes.
- Not introducing pytest-asyncio test patterns; FastAPI sync routes do not need it.
- Not adding mutation testing, property-based testing, or coverage gates. Those are independent decisions.
- Not migrating the existing image-transform tests (`test_adjustments_preview.py`) — they are already pure and fast; leave them in place.
- Not retroactively writing tests for v0.2.x / v0.3.x features unless they touch code paths still under active development. The deferred batch-versioning items are the immediate target.

## Dependent Changes

Once this lands:

- `2026-05-10-batch-version-control` can finally check its Verification box and archive.
- `2026-05-07-v0.3.0-adjustment-panel` can convert its remaining mobile / smoke items into automated TestClient tests where possible.
- `add-frame-ci-cd` can extend its health-gate verification to also gate on the new test suite.
