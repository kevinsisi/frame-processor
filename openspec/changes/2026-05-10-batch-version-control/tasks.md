# Tasks - Batch Version Control

## Spec / Planning

- [x] Compare current `frame-processor` batch behavior against `media-processor` draft versioning.
- [x] Define durable AI batch version model and UX expectations.
- [ ] Confirm plan before product-code implementation.

## Backend

- [ ] Add Alembic migration for `processing_jobs.version_number`, `processing_jobs.archived_at`, retry metadata, and `photo_processing_versions`.
- [ ] Add soft-archive API for completed or failed AI batch versions.
- [ ] Add ORM model for per-photo processing outputs and relationships.
- [ ] Extend API schemas with processing version summaries and `force`.
- [ ] Update project detail response to include project-level and per-photo AI versions.
- [ ] Update processing job creation to compute `version_number`, block duplicates unless `force=true`, and return the new version immediately.
- [ ] Update storage path helper to produce immutable `batch-vN` output paths.
- [ ] Update worker to write immutable paths and insert per-photo version rows.
- [ ] Define `processed_paths[preset]` as latest successful non-archived compatibility cache and recompute it on archive.
- [ ] Add selected AI-version photo download support.
- [ ] Extend export creation to accept a selected AI batch version.
- [ ] Ensure failed/partial versions expose progress/error and never silently fall back to a different version.
- [ ] Add retry flow that creates a new complete version for the original failed/partial job's photo selection.
- [ ] Add secondary retry-missing-only flow that creates a clearly labeled partial retry version.
- [ ] Store and expose per-photo processing status/error for partial failures.
- [ ] Define frontend-owned labels from raw API version/settings fields.
- [ ] Ensure worker file writes and DB rows cannot expose orphaned successful versions.

## Frontend

- [ ] Add TypeScript types for AI batch versions.
- [ ] Add Preview AI version switcher with pending/running/done/failed status chips.
- [ ] Select newly created AI version immediately after pressing **開始產生**.
- [ ] Add AI batch versions to photo card dropdown with user-facing labels.
- [ ] Make selected AI version drive card image, Before/After after-side image, manual adjustment source, and single-photo download.
- [ ] Update automatic generation to reuse matching pending/running/done versions instead of creating duplicates on reload.
- [ ] Add export UI support for downloading the selected AI batch version.
- [ ] Add archive/hide action for unwanted completed/failed AI versions with confirmation.
- [ ] Ensure archiving the selected version switches Preview to the newest valid non-archived version or a clear fallback state.
- [ ] Add retry action for failed/partial versions.
- [ ] Add version settings detail UI for historical AI versions.
- [ ] Show per-photo unavailable/error states for selected partial/failed versions.
- [ ] Label legacy pre-version outputs separately from immutable AI versions.

## Verification

- [ ] Backend unit/integration tests for version numbering, duplicate blocking, force creation, worker outputs, and project detail projection.
- [ ] Tests for failed/partial version visibility and archive behavior.
- [ ] Tests for migration initial version numbering, `force=true`, failed error display projection, per-photo error projection, selected-version export missing-output 409, partial export, processed_paths cache recomputation, settings detail projection, full retry, retry-missing-only, raw-field label generation, and file/DB consistency cleanup.
- [ ] Frontend typecheck and production build.
- [ ] Python lint and full test suite.
- [ ] Compose config validation.
- [ ] Gemini review with `No findings`.
- [ ] Version bump and docs/memory updates.
- [ ] Merge to `main`, push, track CI/CD, and production smoke on `noiseTest`.
