# Tasks - Batch Version Control

## Spec / Planning

- [x] Compare current `frame-processor` batch behavior against `media-processor` draft versioning.
- [x] Define durable AI batch version model and UX expectations.
- [x] Confirm plan before product-code implementation.

## Backend

- [x] Add Alembic migration for `processing_jobs.version_number`, `processing_jobs.archived_at`, retry metadata, and `photo_processing_versions`.
- [x] Add soft-archive API for completed or failed AI batch versions.
- [x] Add ORM model for per-photo processing outputs and relationships.
- [x] Extend API schemas with processing version summaries and `force`.
- [x] Update project detail response to include project-level and per-photo AI versions.
- [x] Update processing job creation to compute `version_number`, block duplicates unless `force=true`, and return the new version immediately.
- [x] Update storage path helper to produce immutable `batch-vN` output paths.
- [x] Update worker to write immutable paths and insert per-photo version rows.
- [x] Define `processed_paths[preset]` as latest successful non-archived compatibility cache and recompute it on archive.
- [x] Add selected AI-version photo download support.
- [x] Extend export creation to accept a selected AI batch version.
- [x] Ensure failed/partial versions expose progress/error and never silently fall back to a different version.
- [x] Add retry flow that creates a new complete version for the original failed/partial job's photo selection.
- [x] Add secondary retry-missing-only flow that creates a clearly labeled partial retry version.
- [x] Store and expose per-photo processing status/error for partial failures.
- [x] Define frontend-owned labels from raw API version/settings fields.
- [x] Ensure worker file writes and DB rows cannot expose orphaned successful versions.

## Frontend

- [x] Add TypeScript types for AI batch versions.
- [x] Add Preview AI version switcher with pending/running/done/failed status chips.
- [x] Select newly created AI version immediately after pressing **開始產生**.
- [x] Add AI batch versions to photo card dropdown with user-facing labels.
- [x] Make selected AI version drive card image, Before/After after-side image, manual adjustment source, and single-photo download.
- [x] Update automatic generation to reuse matching pending/running/done versions instead of creating duplicates on reload.
- [x] Add export UI support for downloading the selected AI batch version.
- [x] Add archive/hide action for unwanted completed/failed AI versions with confirmation.
- [x] Ensure archiving the selected version switches Preview to the newest valid non-archived version or a clear fallback state.
- [x] Add retry action for failed/partial versions.
- [x] Add version settings detail UI for historical AI versions.
- [x] Show per-photo unavailable/error states for selected partial/failed versions.
- [x] Show `未納入此批次` badge on Before/After After-side when active photo has no output in the currently viewed AI version (v0.5.7).
- [x] Label legacy pre-version outputs separately from immutable AI versions.

## Verification

- [x] Pure-function projection tests for `_photo_out` / `_processing_version_out`：done version、failed version 帶 error、多版本順序、processing + adjustment 共存、retry metadata、pending 無 completed_at（`tests/test_project_detail.py`）。
- [ ] **Deferred — needs integration test harness**：DB-bound 測試（`refresh_processing_job_progress`、`recompute_latest_processed_cache`、`update_latest_processed_cache_for_job`）、FastAPI TestClient 測試（`POST /projects/{id}/process` duplicate 409、`force=true`、photo missing 400、`DELETE …/version` archive 行為、selected-version export missing-output 409、partial export、settings detail projection）、worker output 落 immutable path、alembic 0007 migration 初始 version numbering、frontend label 生成 snapshot、file/DB consistency cleanup。整批拆到後續 `add-frame-test-harness` change 才處理（目前 `tests/` 只有 pure-function 測試慣例，沒有 fixture / TestClient / sqlite shim）。
- [x] Frontend typecheck and production build.
- [x] Python lint and full test suite.
- [x] Compose config validation.
- [x] Gemini review with `No findings`.
- [x] Version bump and docs/memory updates.
- [x] Merge to `main`, push, track CI/CD, and production smoke on `noiseTest`.
- [x] Production v0.5.6 follow-up verification on the current 911 batch: live health returned `0.5.6`, AI v14 completed `18/18`, selected AI v13/v14 image requests returned distinct `.ai-v13.jpg` / `.ai-v14.jpg` responses via `processing_job_id`, and Preview code path still maps 「查看版本」 to `processing:<job id>` URLs rather than preset cache URLs.
- [x] v0.5.7 shipped: `未納入此批次` amber badge added to Before/After After-side for photos excluded from the currently viewed AI version.
