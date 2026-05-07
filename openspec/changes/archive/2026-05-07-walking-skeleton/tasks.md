# Tasks — Walking Skeleton

## Backend

- [x] `pyproject.toml` + `requirements.txt`（FastAPI / SQLAlchemy 2 / Alembic / RQ / Pillow / pydantic 2）
- [x] `api/main.py`（app + CORS + router 掛載 + `/health`）
- [x] `api/config.py`（pydantic-settings 讀 env）
- [x] `api/database.py`（engine + sessionmaker + `get_db` dependency）
- [x] `api/queue.py`（Redis + RQ default queue）
- [x] `api/schemas.py`（ProjectCreate / ProjectOut / ProjectDetail / PhotoOut / ExportOut）
- [x] `api/routers/projects.py`（POST/GET 專案 + multipart 上傳）
- [x] `api/routers/photos.py`（GET 原圖 file response）
- [x] `api/routers/exports.py`（POST 觸發 / GET 狀態 / GET 下載）
- [x] `models/database.py` (Base) + `project.py` / `photo.py` / `export.py` / `enums.py`
- [x] `services/storage.py`（`save_original` 寫原圖 + `_read_dimensions` 用 PIL）
- [x] `services/zip_export.py`（`build_zip` + 檔名重複的去重）
- [x] services stubs：`photo_processor.py` / `denoise.py` / `auto_crop.py` / `level_correct.py` / `color_grade.py`（全部 NotImplementedError + 預期介面 docstring）
- [x] alembic：`alembic.ini` + `alembic/env.py` + `alembic/versions/0001_initial.py`

## Worker

- [x] `worker/main.py`（連 redis + 起 RQ worker 監聽 default queue）
- [x] `worker/jobs.py:zip_export_job`（讀 export → run zip_export.build_zip → 更新 status）

## Frontend

- [x] `web/package.json`（React 18 / Vite 5 / Tailwind 3 / TS 5 / react-router-dom）
- [x] tsconfig + vite + tailwind + postcss config
- [x] `src/main.tsx` + `src/App.tsx`（Layout + Router + Nav）
- [x] `src/api/client.ts`（fetch wrapper + endpoint URLs）
- [x] `src/types.ts`（Project / Photo / Export TypeScript types）
- [x] `src/pages/Upload.tsx`（建 project + multipart upload）
- [x] `src/pages/Preview.tsx`（PhotoGrid 看原圖）
- [x] `src/pages/Export.tsx`（觸發 export + polling 狀態 + download link）
- [x] `src/components/Card.tsx` + `PhotoGrid.tsx`

## Deploy

- [x] `deploy/docker-compose.yml`（postgres / redis / api / worker / web 五個服務）
- [x] `deploy/api.Dockerfile`（python:3.11-slim + Pillow native deps + alembic upgrade on entry）
- [x] `deploy/web.Dockerfile`（multi-stage：node:20-alpine 建 + nginx:alpine 服務）
- [x] `deploy/nginx.conf`（SPA fallback）

## Docs

- [x] `CLAUDE.md`（project rules + stack + skill activation）
- [x] `ARCHITECTURE.md`（拓樸 + 資料流 + storage layout + DB schema）
- [x] `ROADMAP.md`（v0.1 → v1.0 phase）
- [x] `README.md`（quick start）
- [x] `.gitignore` + `.env.example` + `.python-version`

## CI

- [x] `.github/workflows/ci.yml`（lint + typecheck + alembic offline check + frontend build）
- [x] `.github/workflows/deploy-dev.yml`（scaffold；v1.0 之前不接真實部署）

## Open Items（轉到 v0.2）

- [ ] HEIC/HEIF 讀取支援（`pillow-heif`）
- [ ] Thumbnail 生成（long edge 600px webp）
- [ ] 第一批 pytest（健康檢查 + 上傳整合測）
- [ ] frontend toast / error boundary
