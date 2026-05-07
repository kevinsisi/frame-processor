# Tasks — v0.2.0 Processing Pipeline

## Backend / Services

- [x] `services/color_grade.py` 實作 `apply_grade(image, preset)`：3 組 preset（純 Pillow + numpy）
- [x] `services/level_correct.py` 實作 `correct_level(image, threshold_deg=5.0)`：Canny + HoughLinesP
- [x] `services/auto_crop.py` 實作 `auto_crop(image, target_aspect)`：Sobel energy + integral image sliding window
- [x] `services/photo_processor.py`：`process_photo(photo, preset, *, level_correct, auto_crop_aspect) -> ProcessedResult` 串 pipeline
- [x] `services/storage.py`：加 `processed_relative_path / processed_absolute_path / thumbnail_*_path / ensure_thumbnail / save_processed_jpeg`

## DB / Models

- [x] `models/enums.py`：加 `ProcessingJobStatus` enum
- [x] `models/processing_job.py`：新 ProcessingJob ORM
- [x] `models/photo.py`：加 `processed_paths` JSONB column
- [x] `models/project.py`：加 `processing_jobs` relationship
- [x] `alembic/versions/0002_processing_jobs.py`：加表 / 加欄位 / 加 enum

## API

- [x] `api/schemas.py`：加 `ProcessingJobCreate`, `ProcessingJobOut`，更新 `PhotoOut.processed_paths`
- [x] `api/routers/processing.py`：`POST /projects/{id}/process`、`GET /processing-jobs/{id}`
- [x] `api/routers/photos.py`：加 `GET /photos/{id}/processed/{preset}`、`GET /photos/{id}/thumbnail`
- [x] `api/main.py`：掛載 processing router、bump version 0.2.0

## Worker

- [x] `worker/jobs.py`：加 `processing_job(job_id, photo_id_strs?)`，呼叫 `services.photo_processor`
- [x] `worker/main.py`：保持不變（worker 監聽 default queue 即可）

## Frontend

- [x] `web/src/types.ts`：加 `ProcessingJobStatus`, `ProcessingJob`, `Photo.processed_paths`, `AutoCropAspect`
- [x] `web/src/api/client.ts`：加 `createProcessing`, `getProcessing`, `processedPhotoUrl`, `thumbnailUrl`
- [x] `web/src/components/BeforeAfter.tsx` + `BeforeAfter.css`：對比拖拉條（純 CSS clip-path）
- [x] `web/src/components/ProcessingProgress.tsx` + `.css`：進度 bar
- [x] `web/src/components/StylePicker.tsx`：加 `level_correct` toggle + `auto_crop_aspect` 下拉
- [x] `web/src/pages/Preview.tsx`：整合 process flow（選 preset → 開始處理 → polling → 顯示 before/after）
- [x] `web/src/version.ts` + `web/package.json`：bump 0.2.0

## Deploy / Deps

- [x] `requirements.txt` + `pyproject.toml`：加 `opencv-python-headless>=4.10`, `numpy>=1.26`
- [x] `deploy/api.Dockerfile`：加 `libgl1` + `libglib2.0-0`
- [x] `pyproject.toml`：bump version 0.2.0
- [x] CI 修整：`pyproject.toml` 加適當 ruff ignores（RUF002/003、B008、UP042 等是專案刻意風格）；`web/package.json` typecheck 改 `tsc -p tsconfig.json --noEmit` 修舊有 `tsc -b --noEmit` 與 composite 衝突

## Docs / Memory

- [x] `ROADMAP.md`：v0.2.0 標 shipped；v0.4/v0.5 改寫成「升級版」（heuristic 已在 v0.2 內 ship）
- [x] `ARCHITECTURE.md`：補 v0.2 處理資料流、pipeline 順序、ProcessingJob 與 processed_paths schema
- [x] memory `version_status.md`：bump 到 v0.2.0 shipped
- [x] CLAUDE.md：現有規則仍適用（enum、worker pipeline、原圖永不覆寫）

## Verification

- [x] 本地 `alembic upgrade head --sql`：0001 + 0002 SQL 產生成功
- [x] 本地 import smoke：`api.main`, `worker.jobs`, `models` 全部 import OK
- [x] 本地 pipeline smoke：合成圖跑完 color_grade + level_correct + auto_crop + photo_processor + thumbnail，1.89s
- [x] `ruff check .` 全部 pass（project 程式碼 0 errors，skill-creator 模板已 exclude）
- [x] `npm run typecheck` 全部 pass
- [x] `npm run build` 全部 pass（vite production build 28s）
- [x] Production deploy 到 `frame.sisihome.org` — 見 commit message 的 deploy 結果
