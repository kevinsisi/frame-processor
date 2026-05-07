# v0.2.0 — 第一條處理 Pipeline

**Status**: shipped — archived 2026-05-07
**Date**: 2026-05-07
**Author**: Kevin

## Why

v0.1.x 已 ship walking skeleton（上傳 → 列表 → 下載 zip），但完全沒有照片處理。
晴晴實際上不會用一個只會搬運原圖的工具；v0.2.0 必須交付第一條完整的處理 pipeline，讓她能感受到「批次後製」的實際價值，並驗證：

1. **Worker pipeline 真的能在 N 張照片上跑完**（v0.1 只跑過 zip job）。
2. **三組色調預設方向是否符合車輛刊登 PoV**（白底展示間 / 戶外暖陽 / 夜拍）— 早確認比晚改方便。
3. **before/after 對比 UI 是否好用** — 後續 NAFNet / YOLO 都會走同個 UI 框架。

這個 phase 把原本拆在 v0.2 / v0.4 / v0.5 的三件事合併成一個「第一條 pipeline」release，用最低 AI 成本（純 Pillow + numpy + Hough line）跑出端到端流程。NAFNet / YOLO 留到 v0.3+ 再加。

## What Changes

提供「上傳 → 選 preset → 一鍵批次處理 → 看 before/after → 下載」的最小完整流程：

### Backend / Pipeline

- `services/color_grade.py`：純 Pillow + numpy 實作三組 preset
  - `SHOWROOM_WHITE`：gray-world 白平衡 + 提亮 + 降飽和
  - `OUTDOOR_WARM`：暖色偏移 + vibrance + 加對比
  - `NIGHT_COLD`：冷色偏移 + 提暗部
- `services/level_correct.py`：OpenCV Canny + HoughLinesP 找近水平線，回傳旋轉角；超過 ±5° 視為誤判不旋轉
- `services/auto_crop.py`：能量圖（Sobel）找最高能量 sub-window，按目標 aspect ratio 裁剪；支援 `original / 3:2 / 4:3 / 16:9 / 1:1 / 9:16`（無 YOLO，v0.4 再升級）
- `services/photo_processor.py`：把上述串成 pipeline `level_correct → auto_crop → color_grade`，每階段獨立可關
- `services/storage.py`：擴充 `processed_path()`、`thumbnail_path()` 與 lazy thumbnail 生成（long edge 600px webp）

### DB

- 新表 `processing_jobs`（id / project_id / preset / level_correct / auto_crop_aspect / status / progress_done / progress_total / error / created_at / completed_at）
- `photos` 增加 `processed_paths` JSONB column：`{ "showroom_white": "projects/<pid>/processed/<photo_id>.showroom_white.jpg", ... }`
- 新 enum `processing_job_status`（pending/running/done/failed）— 與 `export_status` 同值不同名，避免日後語意混淆
- alembic migration `0002_processing_jobs.py`

### API

- `POST /projects/{id}/process` body: `{ preset, photo_ids?, level_correct?, auto_crop_aspect? }` → 建 ProcessingJob + enqueue `worker.jobs.processing_job`，回 ProcessingJobOut
- `GET /processing-jobs/{id}` → 狀態 + 進度
- `GET /photos/{id}/processed/{preset}` → 串流處理後的 jpg
- `GET /photos/{id}/thumbnail` → 串流 webp thumbnail（首次 lazy 生成 + cache）
- 既有 export job 行為不動

### Worker

- 新 job `worker.jobs.processing_job(job_id)`：讀 ProcessingJob → 對每張照片跑 pipeline → 寫 `processed_paths`、更新 progress、整體 status
- 單張失敗不殺整 job，記入 `error` 累計訊息
- 既有 `zip_export_job` 不動

### Frontend

- 新 design pass（依 `skills/frontend-design/SKILL.md` 編輯感 / industrial dark tone 維持 v0.1.1 既有 token）
- `Preview` 頁
  - StylePicker 從 read-only 變成可觸發處理；附 `level_correct` toggle + `auto_crop_aspect` 下拉
  - 處理中 polling ProcessingJob，顯示 N / M 進度
  - 完成後 thumbnail 切到 processed 版本，點擊照片開「before/after slider」對比
- 新 component `BeforeAfter.tsx`：左右對比拖拉條（純 CSS clip-path，不引額外套件）
- 新 component `ProcessingProgress.tsx`：進度 bar + 取消（v0.2 只顯示，不實作 cancel）
- `api/client.ts` 加上 `createProcessing` / `getProcessing` / `processedPhotoUrl` / `thumbnailUrl`
- `types.ts` 加 `ProcessingJob`, `Photo.processed_paths`

### Deploy / Deps

- `requirements.txt` 加 `opencv-python-headless`（>=4.10）+ `numpy` 顯式版本
- `deploy/api.Dockerfile` 加 `libgl1` + `libglib2.0-0`（OpenCV runtime deps；headless 已避開 GUI lib）
- 版本號 bump `pyproject.toml` 與 `api/main.py` 從 `0.1.2` → `0.2.0`
- 部署腳本：`docker compose -f deploy/docker-compose.yml up -d --build`（同 v0.1.x，不變）

## Non-Goals (defer)

- ❌ NAFNet 降噪 — v0.3.0
- ❌ YOLO 主體偵測自動裁剪 — v0.4.0（v0.2 用 energy-based heuristic）
- ❌ 自訂 preset / 曲線 — v0.7.0
- ❌ Cancel processing job — v0.6+
- ❌ 多種 aspect ratio 一次輸出（同一 preset 只能存一份） — v0.6+
- ❌ Thumbnail 在上傳時同步生成（v0.2 lazy on first GET）— 之後若有效能問題再改

## Acceptance Criteria

- `alembic upgrade head` 在乾淨 DB 上能跑出 0001 + 0002
- `docker compose up --build` 五個服務全健康
- 上傳 ≥ 5 張照片 → 選 preset + 開 level_correct + 選 4:3 → 點「開始處理」→ ProcessingJob status 從 pending → running → done
- `/photos/{id}/processed/{preset}` 能拿到處理後 jpg；尺寸已被裁到目標 aspect、傾斜照片有被旋正
- Preview 頁 StylePicker 三個 preset 點下去能各自看到處理結果
- Before/After slider 拖拉左右能切原圖 / 處理後
- Hough line 對明顯傾斜（±2~5°）的照片有效；超過 ±5° 不誤旋轉
- Pipeline 對單張 5MB JPEG 處理時間 < 5 秒（heuristic auto-crop + color grade，CPU only）
- ruff + tsc + alembic offline check 不報錯
- Production deploy 後 `https://frame.sisihome.org/` 能跑完整流程
