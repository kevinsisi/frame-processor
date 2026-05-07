# v0.2.0 — Processing Pipeline (denoise + lens + level + crop + grade)

**Status**: shipped — bundles ROADMAP v0.2 + v0.3 + v0.4 + v0.5 into one release; deployed to https://frame.sisihome.org as v0.2.0 on 2026-05-07. Post-ship iteration in v0.2.1 (per-photo queue progress UI + footer cleanup). Archived 2026-05-07.
**Date**: 2026-05-07
**Author**: Kevin

## Why

v0.1 walking skeleton 已驗證上傳 → 列表 → zip 整條鏈通了。第一個真正能「給晴晴用」的版本必須能對車輛照片做實際後製。

ROADMAP 原本拆 v0.2（色調）/ v0.3（NAFNet 降噪）/ v0.4（自動裁剪）/ v0.5（水平校正）四個 release。實際使用情境是「上傳 N 張 → 一鍵處理出可刊登照片」，四個獨立 release 對使用者沒有意義。決定一次到位，使用者第一次拿到的就是真正可用的工具。

廣角鏡頭桶形畸變是車照常見問題（手機 / 行車記錄器 / 24mm 廣角），原 ROADMAP 沒涵蓋；這次同步加入 lens distortion correction。

## What Changes

提供「批次降噪 + 廣角矯正 + 水平校正 + 自動裁剪 + 套用色調」的一鍵處理 pipeline：

### Backend

- **新增** `services/color_grade.py:apply_grade(image, preset)` — 純 Pillow 三組 preset
- **新增** `services/denoise.py:denoise(image, strength)` — NAFNet-SIDD-width32 inline 架構 + lazy weight download；輕/中/重 三段透過 alpha-blend 控制
- **新增** `services/lens_distort.py:correct_distortion(image)` — OpenCV `cv2.undistort` Brown-Conrady 模型，預設輕度桶形矯正係數 (k1=-0.08, k2=0.02)
- **新增** `services/level_correct.py:correct_level(image)` — Gemini Vision 分析照片回報旋轉角度（無上限，30° 就轉 30°），retry 3 次後 raise；旋轉用 `cv2.warpAffine` + 反推內接矩形裁黑邊
- **新增** `services/auto_crop.py:auto_crop(image, target_aspect)` — Ultralytics YOLOv8n 偵測車輛 (COCO 2/3/5/7) + rule-of-thirds 構圖 + 6 個目標比例
- **新增** `services/photo_processor.py:process_photo(...)` — pipeline orchestrator
- **新增** `models/enums.py`：`AspectRatio`、`DenoiseStrength`、`ProcessingJobStatus`
- **新增** `models/processing_job.py:ProcessingJob` 表
- **新增** `Photo.processed_paths` JSONB column
- **新增** `alembic/versions/0002_processing_pipeline.py`
- **新增** `api/routers/processing_jobs.py`：`POST /projects/{id}/process` + `GET /processing-jobs/{id}`
- **修改** `api/routers/photos.py:GET /photos/{id}/file` 加 `?variant=processed&preset=...`
- **修改** `worker/jobs.py` 加 `process_photos_job`；`zip_export_job` 改成優先打包處理後檔案
- **修改** `services/storage.py` 加 `processed_path` / `relative_to_storage`
- **修改** `api/config.py` 加 `gemini_api_key` / `gemini_model` / `ultralytics_dir` / `nafnet_dir` / `nafnet_tile_size` / `lens_distort_k1` / `lens_distort_k2`

### Frontend

- **新增** `web/src/components/AspectPicker.tsx`、`PipelinePanel.tsx`、`BeforeAfter.tsx`
- **修改** `web/src/pages/Preview.tsx` — PipelinePanel + 進度條 + before/after slider + polling
- **修改** `web/src/api/client.ts` — `createProcessingJob` / `getProcessingJob` / `processedPhotoUrl`
- **修改** `web/src/types.ts` — `AspectRatio` / `DenoiseStrength` / `ProcessingJob` / `ProcessingJobStatus` / `ColorGradePreset`

### Deploy

- **修改** `requirements.txt` 加 `numpy / opencv-python-headless / ultralytics / torch / google-generativeai`
- **修改** `deploy/api.Dockerfile` 加 `libgl1 / libglib2.0-0 / libgomp1`；先安裝 CPU-only torch wheel 再安裝其他
- **修改** `deploy/docker-compose.yml` worker/api 多吃 `GEMINI_API_KEY` `GEMINI_MODEL` `ULTRALYTICS_DIR` `NAFNET_DIR` env；模型權重 lazy download 寫到 `/data/models-weights/{ultralytics,nafnet}`，跨 container restart 共用

### Docs

- **修改** `ROADMAP.md` v0.2.0 改為 bundled scope；v0.3 / v0.4 / v0.5 標 merged-forward
- **修改** `ARCHITECTURE.md` 加 ProcessingJob 表 + processing 資料流 + storage layout 補 processed
- **修改** `CLAUDE.md` bump version、加 Gemini key + NAFNet weights 部署 note
- **新增** `docs/adr/0002-bundled-v0.2.0-processing.md`

## Non-Goals (defer)

- ❌ 自訂 preset / 自訂裁剪框微調 — v0.7.0
- ❌ 處理進度即時 push (SSE/WebSocket) — 仍走 polling
- ❌ 多 preset 平行輸出 — 一次只跑一組
- ❌ Thumbnail 預生成
- ❌ GPU worker 拆分 — 同 image 用 `torch.cuda.is_available()` 自動偵測
- ❌ 自訂 lens distortion 參數 UI — 由 backend env / settings 調

## Acceptance Criteria

- `POST /projects/{id}/process {preset, denoise_strength, lens_distort_correct, level_correct, auto_crop_aspect}` 回 202 ProcessingJob
- worker pick up job → 對每張 photo 跑 pipeline → 寫 `processed/{photo_id}.{preset}.jpg`
- `GET /processing-jobs/{id}` 顯示 progress 從 0 / total 增到 total / total 後 status=done
- `GET /photos/{id}/file?variant=processed&preset=...` 串流處理後檔案
- `POST /projects/{id}/exports` 在有 processed 結果時打包處理後檔案
- FE Preview 頁能選 preset + denoise + lens + level + aspect → 按開始 → 進度條 → 完成後 before/after slider
- alembic `upgrade head` + `downgrade -1` 都成功
- `docker compose build` 成功；`up -d` 起來後 `/health` 回 v0.2.0
- 設定 `GEMINI_API_KEY` 後 level_correct 對歪 30° 樣本能轉回水平
