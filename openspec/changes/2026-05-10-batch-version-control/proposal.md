# v0.4.0 - Batch Version Control

**Status**: proposed
**Date**: 2026-05-10
**Author**: Kevin

## Why

`frame-processor` currently has two different version concepts:

- Manual adjustments create immutable `manual-vN` files and `photo_adjustment_versions` rows.
- Batch AI processing overwrites the same `<photo_id>.<preset>.jpg` path for the same preset.

This means pressing **開始產生** multiple times can destroy the previous AI batch output, especially when the user changes denoise, lens correction, level correction, crop aspect, or style settings. Kevin wants the workflow to match `media-processor`: each generation creates a durable version that can be revisited, compared, and downloaded later.

## What Changes

### Backend

- Treat each `ProcessingJob` as a durable AI batch version, similar to `media-processor` `Draft` rows.
- Add `version_number` to `processing_jobs`, unique per project.
- Add a per-photo batch output table, e.g. `photo_processing_versions`, mapping:
  - processing job / batch version id
  - project id
  - photo id
  - version number
  - preset and processing settings snapshot
  - output path
  - created_at
- Store batch output files as immutable version paths, e.g. `processed/<photo_id>.batch-v<N>.jpg`, not `<photo_id>.<preset>.jpg`.
- Keep `Photo.processed_paths` as compatibility/cache for latest-by-preset output where useful, but do not use it as the source of truth for version history.
- `POST /projects/{id}/process` creates the version row synchronously before enqueueing work and returns `version_number` in the job response.
- Default behavior mirrors `media-processor`: if a project already has a pending/running batch version, return `409` unless the request explicitly passes `force=true`.
- `GET /projects/{id}` returns batch version summaries so the UI can render version chips/dropdowns without inspecting raw path keys.
- `GET /photos/{id}/file` or a companion endpoint supports downloading a specific batch version output.
- Export ZIP can target a selected batch version instead of always using the latest adjusted/preset fallback.

### Worker / Storage

- Worker writes each generated photo to the job's immutable version path.
- Worker records a `photo_processing_versions` row per completed photo.
- Failed jobs keep their version row with failed status and error so users can see what happened.
- Re-running the same settings creates `vN+1`; no output files are overwritten.

### Frontend

- Preview page shows an AI batch version switcher, similar to `media-processor` draft chips:
  - `AI v1`, `AI v2`, ... with status labels pending/running/done/failed.
  - Newly submitted versions are selected immediately while the job runs.
  - Old versions stay selectable after newer versions finish.
- Photo card version dropdown includes batch versions with user-facing labels, e.g. `AI v3 - 展示間白 / 中度降噪`.
- Every historical AI version exposes its full pipeline settings snapshot in the UI, including preset, denoise strength, lens correction, level correction, crop aspect, created time, status, progress, and error if any.
- Selecting a batch version changes:
  - card image
  - top Before/After after-side image
  - manual adjustment source
  - single-photo download target
- Export controls can download a ZIP for the currently selected AI batch version.
- Users can hide/archive an unwanted AI batch version from the Preview version list after confirmation. This is a soft delete: the version is excluded from UI/export selection, but files are not physically removed in v0.4.0.
- Failed/partial AI versions offer a retry action that creates a new complete version for the original photo selection; immutable versions are never repaired in place.
- Large partial failures also offer a secondary **retry missing only** action; it still creates a new version and labels it as a partial retry, so the original version remains immutable and understandable.
- Automatic background generation must avoid spamming versions on every page reload. It should only create a new version when there is no existing done/pending/running version matching the current pipeline settings for the needed photos.

## Non-Goals

- Do not change manual adjustment versioning; `manual-vN` remains independent.
- Do not delete or migrate old processed files unless a safe migration is explicitly needed.
- Do not add visual diff tooling beyond the existing Before/After viewer.
- Do not make batch versions editable in place; any rerun creates a new version.
- Do not physically delete version files from storage in v0.4.0; archive/hide is enough for lifecycle control and safer for production data.
- Do not support unarchive or permanent delete in v0.4.0; archived versions remain recoverable from the database by an operator if needed.

## Acceptance Criteria

- Pressing **開始產生** creates a new `AI vN` every time, without overwriting prior AI outputs.
- The new version appears immediately in Preview while pending/running.
- When a job completes, users can switch between old and new AI versions in Preview.
- Photo cards and Before/After use the selected batch version, not only the latest preset path.
- Single-photo download can download an old AI batch version.
- ZIP export can target a selected AI batch version.
- A ZIP export for a specific AI batch version contains only outputs from that version. If selected photos are missing from that version, export creation fails with a clear missing-photo message instead of mixing other versions.
- Partial-version export defaults to fail-fast when outputs are missing, but the UI can explicitly choose **export available only** to download just the successful photos from that selected version.
- Duplicate accidental clicks are still blocked while a job is pending/running unless `force=true` is explicitly used.
- `force=true` explicitly bypasses the duplicate in-flight block and creates the next version number.
- Auto-generation does not create a new version repeatedly on every reload for the same current settings.
- A failed or partially completed version remains visible with clear status (`failed`, progress count, and error text); photos that did finish remain selectable, while missing outputs show a clear unavailable state instead of silently falling back to another version.
- Failed job error messages are visible in the Preview UI.
- Retrying a failed/partial version creates a new `AI vN+1` for the same original photo selection, so the retry produces one complete comparable version instead of splitting a logical batch across versions.
- Retrying missing photos only creates a new clearly-labeled partial retry version and never mutates the failed version.
- Users can archive/hide an unwanted AI version after confirmation, and archived versions no longer appear in default selectors or exports.
- Archiving the version currently cached in `processed_paths[preset]` recomputes that cache to the next-newest successful non-archived output, or removes the preset key when none exists.
- Users can inspect full pipeline settings for any historical AI version before comparing, exporting, retrying, or archiving it.
- If the user archives the currently selected AI version, Preview automatically switches to the newest available non-archived version; if none exists, it switches to legacy output or original with a clear empty-state message.
- Partial versions show per-photo status/error, so a photo outside the selected version or failed inside it is visibly unavailable instead of silently falling back.
- In a selected partial/failed version, unavailable photo tiles show a disabled-looking thumbnail state with a `此版本無輸出` / `處理失敗` label, expose the per-photo error when present, and do not offer that version as a valid download for the photo.
- Legacy pre-version outputs are labeled `舊批次輸出` and visually separated from immutable `AI vN` versions.
- If the worker writes an output file but fails to record the version DB row, it cleans up that newly written file and does not expose a successful version in the UI/API.
- Existing manual versions and adjusted export priority keep working.
- Existing projects with only `processed_paths` continue to display their latest preset output as a legacy batch option or fallback.
- Existing projects with no prior AI version rows start their first new immutable AI batch at `AI v1` after migration.

## Open Questions

1. **Project-level vs per-photo version selection**
   - Recommendation: default Preview selection is project-level AI version; per-photo dropdown can override only when needed.

2. **Legacy outputs**
   - Recommendation: surface current `processed_paths[preset]` as `Legacy batch` fallback when no version rows exist; new runs use immutable version rows.

3. **Export priority**
   - Recommendation: if a batch version is explicitly selected, export that version for photos where it exists, then manual adjusted only when the user explicitly selects adjusted/manual. This avoids silently mixing outputs from different generations.

4. **Version scope for partial photo selections**
   - Recommendation: still create one project-level `AI vN`; photos not included simply have no output in that version and fall back visually with a clear missing-output state.
