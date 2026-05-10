# Design - Batch Version Control

## Reference Behavior

`media-processor` creates a durable `Draft` row before a render starts:

- `version = max(project.drafts.version) + 1`
- row starts as pending
- UI immediately selects the new draft id
- worker updates status and output paths
- old drafts remain selectable
- pending/processing draft blocks accidental duplicate creation unless `force=true`

`frame-processor` should follow the same mental model for AI batch processing.

## Data Model

### Extend `processing_jobs`

Add:

- `version_number int not null`
- `archived_at timestamptz null`
- `retry_scope varchar(32) not null default 'none'`
- `retry_of_job_id uuid null references processing_jobs(id)`
- unique constraint `(project_id, version_number)`

The existing `processing_jobs` table already stores project id, status, selected photos, progress, error, preset, denoise, lens, level, crop, timestamps. Reusing it avoids a second project-level version table and keeps queued/running/done status in one place.

`retry_scope` values:

- `none` - normal user or automatic generation
- `full` - retry of a failed/partial version using the original photo selection
- `missing_only` - retry of failed/missing photos only

### Add `photo_processing_versions`

Proposed columns:

- `id uuid primary key`
- `processing_job_id uuid references processing_jobs(id) on delete cascade`
- `photo_id uuid references photos(id) on delete cascade`
- `status varchar(32) not null`
- `path varchar(512) null`
- `error text null`
- `created_at timestamptz not null default now()`

Indexes:

- unique `(processing_job_id, photo_id)`

Reasoning:

- Project version metadata lives on `ProcessingJob`.
- Per-photo output paths live in a normalized table instead of expanding `processed_paths` with opaque dynamic keys.
- Settings and version metadata are read through the `processing_job_id` relationship to avoid duplicated values drifting.

`photo_processing_versions.status` values:

- `done` - `path` is present and points to the successful output
- `failed` - `path` is null and `error` explains why this photo has no output in the selected version

## Storage Paths

New batch outputs:

```text
projects/<project_id>/processed/<photo_id>.batch-v<version_number>.jpg
```

Existing manual paths stay unchanged:

```text
projects/<project_id>/processed/<photo_id>.manual-v<N>.jpg
```

Existing latest preset paths can remain for compatibility but should no longer be the canonical version source.

Compatibility cache rule:

- Only fully successful AI versions update `Photo.processed_paths[preset]` to the newest successful, non-archived output for that preset.
- Failed/partial versions never update `processed_paths`, even if some photos produced valid outputs.
- Retried versions update the cache only when that retry job fully succeeds.
- Archiving the newest version recomputes the cache to the next-newest successful, non-archived output for that preset, or removes that preset key if none exists.
- Version-aware UI and exports must use `photo_processing_versions`; `processed_paths` is only a legacy/latest cache.

## API Shape

### `ProcessingJobCreate`

Add:

- `force: bool = false`

### `ProcessingJobOut`

Add:

- `version_number: int`

### Project detail

Add `processing_versions` sorted newest first:

```json
{
  "id": "job uuid",
  "project_id": "project uuid",
  "version_number": 3,
  "status": "done",
  "preset": "showroom_white",
  "denoise_strength": "medium",
  "lens_distort_correct": true,
  "level_correct": true,
  "auto_crop_aspect": null,
  "photo_ids": ["..."],
  "progress": 3,
  "total": 3,
  "error": null,
  "created_at": "...",
  "completed_at": "..."
}
```

Each `PhotoOut` adds `processing_versions` for outputs that exist for that photo:

```json
{
  "processing_job_id": "job uuid",
  "version_number": 3,
  "status": "done",
  "path": "projects/.../processed/<photo>.batch-v3.jpg",
  "error": null,
  "created_at": "..."
}
```

The API returns raw version fields. Frontend constructs localized labels such as `AI v3 - 展示間白 / 中度降噪`.

### Download

Either extend `GET /photos/{id}/file` with `processing_job_id`, or add:

```text
GET /photos/{id}/processing-versions/{job_id}/file
```

Use explicit job id over version number so partial versions and future retries remain unambiguous.

### Archive

Add a soft-delete endpoint:

```text
DELETE /processing-jobs/{job_id}/version
```

Behavior:

- Sets `processing_jobs.archived_at`.
- Refuses to archive pending/running jobs with `409`; users must wait for completion/failure first.
- Does not delete files or `photo_processing_versions` rows in v0.4.0.
- Project detail excludes archived versions by default.

### Export

Extend `ExportCreate` with:

- `processing_job_id?: UUID`

When present, export uses only outputs from the selected batch version for included photos. If any selected photo has no successful output in that version, export creation returns `409` with missing photo ids by default. `allow_partial=true` exports only successful outputs from that selected version. No silent cross-version mixing.

## Worker Flow

1. API validates photos and in-flight jobs.
2. API computes `next_version = max(ProcessingJob.version_number for project) + 1`.
3. API creates pending `ProcessingJob(version_number=next_version)` and enqueues the worker.
4. UI selects the returned job id immediately.
5. Worker processes each photo and writes `batch-vN` path for successful photos.
6. Worker inserts or updates `photo_processing_versions` for `(job_id, photo_id)` with status `done` + path or status `failed` + error.
7. Worker updates `processed_paths[preset]` only after every requested photo succeeds.
8. Worker marks job done/failed.

File/DB consistency rule:

- Worker writes to a `.part` file first.
- Worker renames to the immutable final path only after the image save succeeds.
- Worker records the DB row immediately after final rename.
- If the DB write fails after final rename, worker attempts to remove the newly written file before marking the photo/job failed.
- Tests must cover that DB failure after file write does not leave the version visible without a DB row.

Partial failure behavior:

- If some photos finish before a failure, their `photo_processing_versions` rows remain valid.
- Failed photos get rows with per-photo error text.
- The job status becomes `failed` when any requested photo fails; `progress` shows attempted count, and `error` stores a summary.
- UI must not silently fall back to another version for photos missing or failed in that selected version; it should show that the selected AI version has no successful output for that photo.
- Default retry creates a new `ProcessingJob` with the same `photo_ids` as the original failed/partial job and `version_number = max + 1`; immutable failed versions are not mutated. This produces one complete comparable retry version instead of splitting the corrected batch across multiple version numbers.
- Secondary retry-missing-only creates a new partial retry version with `retry_scope='missing_only'` and only failed/missing photo ids for large batches where speed matters more than one complete comparable set.

## Frontend Flow

### Version Switcher

Preview renders a project-level AI version switcher above the comparison area or near the sticky pipeline summary:

- chips show `AI vN` and status
- failed chips show progress and expose the error message in title/detail text
- each chip or adjacent detail area exposes the full settings snapshot: preset, denoise, lens, level, crop aspect, created time, status, progress, and error
- latest version selected by default
- submitting a new job selects it immediately
- archived versions are hidden from default selectors
- failed/partial versions show a retry action for missing photos
- archiving the selected version switches selection to the newest non-archived version; if none exists, the selected AI version becomes null and the UI falls back to legacy output/original with a clear message
- selected partial/failed versions show per-photo status, including failed photo errors and photos not included in the selected version

### Photo Card Dropdown

Options order:

1. Manual versions `手動版本 vN`
2. AI batch versions `AI vN - <preset> / <denoise>`
3. Legacy batch output labeled `舊批次輸出` if no version row exists
4. Original

### Auto Generation

Before creating an automatic version, check whether an existing pending/running/done `ProcessingJob` matches:

- preset
- denoise_strength
- lens_distort_correct
- level_correct
- auto_crop_aspect
- required photo ids are covered

If yes, select or wait for that version instead of creating another.

## Migration / Compatibility

- Add nullable/default-safe columns and tables through Alembic.
- Existing `processed_paths` data remains readable.
- Do not try to reconstruct historic version rows from overwritten preset files.
- First new run after migration creates `AI v1`.
- Legacy outputs display as `批次：<preset>` or `舊批次輸出` until a real AI version exists.
- Archived versions remain in the database for audit/recovery but are omitted from normal project detail selectors.
- Unarchive and permanent delete are out of scope for v0.4.0.

## Testing Strategy

- Backend tests:
  - first job gets version 1
  - second completed/rerun job gets version 2 and preserves v1 path
  - pending/running job returns 409 without force
  - force creates a new version
  - worker writes `batch-vN` and `photo_processing_versions`
  - project detail returns version summaries
  - selected-version download resolves the immutable path
- Frontend tests/build:
  - TypeScript covers new API types
  - version dropdown labels and values include `processing:<job_id>`
  - Preview selects newly created job id after submit
- Smoke:
  - On production `noiseTest`, generate two AI versions with different denoise settings and verify both remain selectable.
