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
- [x] Label legacy pre-version outputs separately from immutable AI versions.

## Verification

- [ ] Backend unit/integration tests for version numbering, duplicate blocking, force creation, worker outputs, and project detail projection.
- [ ] Tests for failed/partial version visibility and archive behavior.
- [ ] Tests for migration initial version numbering, `force=true`, failed error display projection, per-photo error projection, selected-version export missing-output 409, partial export, processed_paths cache recomputation, settings detail projection, full retry, retry-missing-only, raw-field label generation, and file/DB consistency cleanup.
- [x] Frontend typecheck and production build.
- [x] Python lint and full test suite.
- [x] Compose config validation.
- [x] Gemini review with `No findings`.
- [x] Version bump and docs/memory updates.
- [ ] Merge to `main`, push, track CI/CD, and production smoke on `noiseTest`.
