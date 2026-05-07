# ROADMAP

照片批次後製工具的路線圖。版本號採語意化版本（major.minor.patch）。

每個 phase 都有對應的 `openspec/changes/<change-id>/` 提案；提案 archive 後填入「狀態 / 對應提案」連結。

---

## v0.1.0 — Walking Skeleton ✅ (current)

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

對應提案：`openspec/changes/2026-05-07-walking-skeleton/`

---

## v0.2.0 — Pillow 色調預設（無 AI）

**目標**：第一個真正的處理 pipeline。用純 Pillow 實作三組色調 preset，驗證 worker pipeline + 前後對比 UI。

範圍：
- `services/color_grade.py` 實作三組 preset：
  - `SHOWROOM_WHITE`（展示間白）— 白平衡矯正、輕度提亮、降低色彩飽和度
  - `OUTDOOR_WARM`（戶外暖調）— 暖色偏移、輕微 vibrance、增加對比
  - `NIGHT_COLD`（夜拍冷調）— 冷色偏移、降低噪點靠 blur（暫定）、提暗部
- `models/enums.py:ColorGradePreset` enum 三項
- `POST /projects/{id}/process`：建立 ProcessingJob，enqueue 至 RQ；body 含 `preset` 與 `photo_ids`（空陣列代表全選）
- `GET /processing-jobs/{id}` 查狀態 + 進度 + per-photo 結果路徑
- FE Preview 頁支援前後對比 slider（同一張照片左右拖拉）
- DB 新增 `ProcessingJob` 表 + `Photo.processed_paths` JSON column（key=preset name, value=檔案路徑）

非範圍（defer 到後續 phase）：
- AI 降噪、自動裁剪、水平校正
- 自訂預設（v0.7+）

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

## v0.4.0 — 自動裁剪 AI（構圖）

範圍：
- `services/auto_crop.py`：以 YOLO 偵測車輛主體 + 三分構圖規則，輸出建議裁剪框
- 支援目標比例：原始、3:2、4:3、16:9、IG 1:1、IG 9:16
- ProcessingJob 新增 `target_aspect` 欄位
- FE Preview 頁顯示建議裁剪框可微調

---

## v0.5.0 — 水平校正

範圍：
- `services/level_correct.py`：以 Hough line detection 找主水平線，旋轉至水平
- 對車身底盤線、地平線、展示間地板邊有效；對晃動車內照片可能誤判，需有「跳過此張」開關
- ProcessingJob 新增 `level_correct: bool`

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
