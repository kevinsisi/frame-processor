# Tasks — v0.2.0 Processing Pipeline

## Schema / Models

- [x] `models/enums.py` 加 `AspectRatio`、`DenoiseStrength`、`ProcessingJobStatus`
- [x] `models/processing_job.py` 新檔
- [x] `models/photo.py` 加 `processed_paths` JSONB column
- [x] `models/project.py` 加 `processing_jobs` relationship
- [x] `models/__init__.py` export `ProcessingJob`
- [x] `alembic/versions/0002_processing_pipeline.py`

## Services

- [x] `services/color_grade.py` 三組 preset
- [x] `services/denoise.py` NAFNet inline + lazy weight download + tile + blend
- [x] `services/lens_distort.py` cv2.undistort
- [x] `services/level_correct.py` Gemini Vision + retry + warpAffine
- [x] `services/auto_crop.py` YOLOv8n + rule-of-thirds + 6 aspects
- [x] `services/photo_processor.py` orchestrator
- [x] `services/storage.py` 加 `processed_path` / `relative_to_storage`

## API

- [x] `api/config.py` 加 Gemini key + 模型權重路徑 + tile size + lens 係數
- [x] `api/schemas.py` 加 `ProcessingJobCreate` / `ProcessingJobOut` + denoise/lens/aspect
- [x] `api/routers/processing_jobs.py` 新 router
- [x] `api/routers/photos.py` 加 `?variant=processed&preset=...`
- [x] `api/main.py` 掛 router、bump version 0.2.0

## Worker

- [x] `worker/jobs.py:process_photos_job`
- [x] `worker/jobs.py:zip_export_job` 改成優先打包處理後檔案
- [x] queue timeout 1800s

## Deploy

- [x] `requirements.txt` 加 numpy / opencv-headless / ultralytics / torch / google-generativeai
- [x] `deploy/api.Dockerfile` 加 libgl1 / libglib2.0-0 / libgomp1 + CPU torch wheel
- [x] `deploy/docker-compose.yml` 加 GEMINI_API_KEY / GEMINI_MODEL / ULTRALYTICS_DIR / NAFNET_DIR / YOLO_CONFIG_DIR env

## Frontend

- [x] `web/src/types.ts` ProcessingJob / DenoiseStrength / AspectRatio 等
- [x] `web/src/api/client.ts` processing endpoints
- [x] `web/src/components/AspectPicker.tsx` + css
- [x] `web/src/components/PipelinePanel.tsx` + css
- [x] `web/src/components/BeforeAfter.tsx` + css
- [x] `web/src/pages/Preview.tsx` 整合 PipelinePanel + 進度 + before/after

## Docs / Memory

- [ ] `ROADMAP.md` v0.2.0 改 bundled scope；v0.3 / v0.4 / v0.5 標 merged-forward
- [ ] `ARCHITECTURE.md` 加 ProcessingJob 表 + processing 資料流
- [ ] `CLAUDE.md` bump version + Gemini key + NAFNet weights note
- [ ] `docs/adr/0002-bundled-v0.2.0-processing.md`
- [ ] memory `version_status.md` update 到 v0.2.0

## Verify / Ship

- [ ] `python -c "import api.main, worker.jobs, services.photo_processor"` smoke import
- [ ] `cd web && npm run build`
- [ ] commit on Kevin
- [ ] push origin
- [ ] ssh `100.83.112.20` → `cd ~/DockerCompose/frame-processor` → `git pull` → `docker compose -f deploy/docker-compose.yml up -d --build`
- [ ] verify `https://frame.sisihome.org/health` returns v0.2.0
