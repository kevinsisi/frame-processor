# ROADMAP

照片批次後製工具的路線圖。版本號採語意化版本（major.minor.patch）。

每個 phase 都有對應的 `openspec/changes/<change-id>/` 提案；提案 archive 後填入「狀態 / 對應提案」連結。

---

## v0.1.x — Walking Skeleton ✅ (shipped)

**目標**：上傳 N 張 → 存 disk + DB → 列表 → 下載 zip。**沒有任何照片處理**，純粹驗收 stack 整條鏈通了。

驗收：
- [x] FastAPI 啟動成功，`GET /health` 回 200
- [x] React + Vite + Tailwind 啟動成功，`/upload` `/preview` `/export` 三頁能渲染
- [x] PostgreSQL + alembic migration 0001 建立 Project / Photo / Export 表
- [x] `POST /projects` 建立專案
- [x] `POST /projects/{id}/photos`（multipart）上傳多張並存 disk
- [x] `GET /projects/{id}` 列出該專案 photos
- [x] `GET /photos/{id}/file` 串流原圖
- [x] `POST /projects/{id}/exports` 觸發 RQ worker job 打包 zip
- [x] `GET /exports/{id}/download` 下載 zip
- [x] `docker compose up` 五個服務全起來

子版本：

- **v0.1.0** — 初版 scaffold（commit `c4a6677`）。
- **v0.1.1** — Editorial / cinematic dark theme 前端改版（合併 `claude/romantic-cannon-38c856`）：tokens.css 設計系統、AppHeader / AppFooter / Dropzone / StylePicker / Spinner / Toast、三頁 (Upload / Preview / Export) 全部翻新。
- **v0.1.2** — Production deploy 到 `https://frame.sisihome.org`（合併 `claude/stupefied-mendel-e3664e`）：docker-compose 對外只開 web container 8533、nginx `/api/*` reverse proxy 到 `api:8000`、`VITE_API_BASE_URL=/api`、API `ALLOWED_ORIGINS` 含 frame.sisihome.org、RPi Caddy `request_body.max_size 500MB`。alembic 0001 修小問題，web 加 `@types/node`。

對應提案：`openspec/changes/archive/2026-05-07-walking-skeleton/`（已 archive）

---

## v0.2.0 — 第一條處理 Pipeline ✅ (shipped)

**目標**：第一條真正的批次後製 pipeline。把原本拆在 v0.2 / v0.4 / v0.5 的色調 / 自動裁剪 / 水平校正合併成一個 release，全部用 CPU heuristic 實作（無 AI），把 worker pipeline + before/after UI 跑通。

範圍：
- `services/color_grade.py` 三組 preset（純 Pillow + numpy）：
  - `SHOWROOM_WHITE` — gray-world 白平衡 + 輕度提亮 + 降飽和
  - `OUTDOOR_WARM` — 暖色偏移 + vibrance + 加對比
  - `NIGHT_COLD` — 冷色偏移 + gamma 提暗部
- `services/level_correct.py` — Canny + HoughLinesP 找近水平線；旋轉量超過 ±5° 視為誤判不轉
- `services/auto_crop.py` — Sobel energy + integral image，按 `original / 3:2 / 4:3 / 16:9 / 1:1 / 9:16` 裁剪
- `services/photo_processor.py` — Pipeline 串接 `level_correct → auto_crop → color_grade`
- DB：`processing_jobs` 表（preset / level_correct / auto_crop_aspect / status / 進度）+ `photos.processed_paths` JSONB
- API：`POST /projects/{id}/process`、`GET /processing-jobs/{id}`、`GET /photos/{id}/processed/{preset}`、`GET /photos/{id}/thumbnail`（lazy webp 600px）
- Worker：`worker.jobs.processing_job`（單張失敗不殺整 job）
- FE：Preview 頁整合處理流程（StylePicker + 水平校正 toggle + 裁剪比例下拉）+ ProcessingProgress + BeforeAfter slider（純 CSS clip-path）
- Deploy：`opencv-python-headless` + `numpy`，Dockerfile 加 `libgl1` + `libglib2.0-0`

對應提案：`openspec/changes/2026-05-07-v0.2.0-processing-pipeline/`

---

## v0.3.0 — NAFNet AI 降噪

整合 NAFNet 預訓練模型對單張照片做降噪。串接到處理 pipeline，可在套用 color preset 前先執行。

範圍：
- `services/denoise.py` 載入 NAFNet 權重，提供 `denoise(image: PIL.Image) -> PIL.Image`
- 模型權重存放：`models-weights/nafnet/...`（Docker volume mount，不入 git）
- 加 GPU runtime 偵測：有 CUDA 用 GPU，否則 CPU 並提醒處理時間長
- ProcessingJob 新增 `denoise: bool` 旗標
- ROADMAP 與 ADR 補充：為何選 NAFNet 而不是 Real-ESRGAN / SCUNet

---

## v0.4.0 — 自動裁剪升級（YOLO 主體偵測）

v0.2 已有 energy-based heuristic 自動裁剪做為 v0.x baseline；v0.4 升級為 YOLO 主體偵測 + 三分構圖。

範圍：
- `services/auto_crop.py`：以 YOLOv8 偵測車輛主體框，配合三分構圖規則微調 v0.2 的 energy crop window
- 主體保持 70% 完整度約束（不切到車輪、車燈）
- FE Preview 頁顯示建議裁剪框可微調拖拉

---

## v0.5.0 — 水平校正升級

v0.2 已有 Hough line heuristic；v0.5 升級為更穩定的演算法（例如 multi-scale Hough、車身底盤線優先）。

範圍：
- `services/level_correct.py`：對特殊角度照片提供「跳過此張」單張開關
- 對展示間地板格線、車身底盤線、地平線各自有專門 detector
- 旋轉量信心度低於閾值時自動 skip 並回報原因

---

## v0.6.0 — 完整 pipeline + Preset 組合

把 v0.2–v0.5 串成一條 pipeline：denoise → level_correct → auto_crop → color_grade。

範圍：
- 一鍵套用 preset bundle（例如「展示間白完整版」= 降噪 ON + 水平校正 ON + 裁剪 4:3 + 色調白）
- FE 提供 3 個預設 bundle + 自訂進階模式
- 處理進度顯示每階段細項

---

## v0.7.0 — 自訂 preset

使用者儲存自己的色調曲線、裁剪偏好。

---

## v0.8.0 — 認證 + 8891 整合

範圍：
- 簡易 password / SSO 登入（單一使用者：晴晴）
- 處理完的照片可一鍵推送到 8891 刊登流程（與 carsmeet 後台對接，視 `_car-maintain` 專案 API 而定）

---

## v1.0.0 — Production Ready

範圍：
- Production Docker 部署到 frame.sisihome.org（domain 待定）
- HTTPS（Cloudflare Tunnel 或 reverse proxy）
- 監控 / 日誌 / 自動備份
- 對應 `_car-maintain` 的 carsmeet 入口連結

---

## 維護筆記

- v0.x 期間 schema 不保證向下相容，alembic migration 直接 destructive 改 schema 也可。v1.0 之後才開始守 backwards compat。
- 所有照片儲存路徑慣例見 `ARCHITECTURE.md` § Storage Layout。
- 模型權重不入 git，由 deploy 流程或第一次啟動 lazy-download。
