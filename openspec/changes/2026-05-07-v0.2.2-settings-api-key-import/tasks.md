# Tasks — v0.2.2 Settings Page + API Key Import

## Backend

- [x] Add `models/app_setting.py` and export it from `models/__init__.py`.
- [x] Add alembic migration `0003_app_settings.py`.
- [x] Add `services/settings_store.py` with Gemini key parsing, summary, DB/env fallback, set, clear, and key-manager sync helpers.
- [x] Add `api/routers/settings.py` and mount it in `api/main.py`.
- [x] Make level correction resolve the active Gemini key via settings store.
- [x] Require `SETTINGS_ADMIN_TOKEN` for key mutations and use backend `KEY_MANAGER_URL` only.
- [x] Add OpenCV denoise fallback when NAFNet weights cannot be downloaded.

## Frontend

- [x] Add settings types and API client methods.
- [x] Add `web/src/pages/Settings.tsx` and `Settings.css`, using media-processor as UX reference.
- [x] Add `/settings` route and header navigation link.
- [x] Fix mobile header/pipeline/job-status overflow and before-after slider clipping.

## Version / Docs

- [x] Bump version to `0.2.2` in Python and web version files.
- [x] Update README/CLAUDE/ROADMAP if needed.

## Verification

- [x] `py -3 -c "import api.main, services.settings_store, services.level_correct"`
- [x] `cd web && npm run build`
- [x] Pre-commit reviewer returns `No findings`.
- [x] Commit with Kevin identity and push.
