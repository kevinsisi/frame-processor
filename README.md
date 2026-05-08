# frame-processor

照片批次後製工具。上傳 N 張 → 選 preset + 處理選項 → 全部一鍵處理 → 下載 zip。

目前狀態：**v0.3.0 in progress — bundled pipeline + settings key import + manual adjustment panel**（NAFNet AI 降噪 / 廣角畸變矯正 / Gemini Vision 水平校正 / YOLOv8 自動裁剪 / Pillow 色調 preset / before-after 對比 / per-photo queue progress / Gemini key 設定頁 / 手動曝光、對比、亮暗部、色溫、色偏、飽和、自然飽和、清晰度、銳利化、HSL 微調與 preset 儲存載入）。已部署至 [frame.sisihome.org](https://frame.sisihome.org)。

## Quick start

```bash
# 1. 起服務
cd deploy
docker compose up -d --build

# 2. 開瀏覽器
# Web UI:  https://frame.sisihome.org   （或本機 http://localhost:8533 / dev http://localhost:5173）
# API doc: 經 nginx → /api/docs           （或本機 http://localhost:8633/docs）
```

> alembic migration 由 api container 啟動時自動跑（`alembic upgrade head` 寫死在 entrypoint）。

### 必要環境變數

`deploy/docker-compose.yml` 從同目錄 `deploy/.env` 讀取（或主機 env 直接 inject）：

```bash
GEMINI_API_KEY=xxx          # 水平校正必要（Gemini Vision 估角度）；缺則 level_correct 會 fail
GEMINI_MODEL=gemini-2.5-flash   # 預設值
SETTINGS_ADMIN_TOKEN=xxx    # /settings 修改金鑰必要；只用於 PUT/DELETE/sync mutation
KEY_MANAGER_URL=            # 可選；空白代表不啟用 key-manager 同步，直接貼 key 即可
ULTRALYTICS_DIR=/data/models-weights/ultralytics  # YOLOv8 權重 cache
NAFNET_DIR=/data/models-weights/nafnet            # NAFNet 權重 cache
```

模型權重（YOLOv8n 6MB + NAFNet-SIDD-width32 ~67MB）首次處理時 lazy download 到對應 volume 路徑，之後跨 container restart 共用。

## 開發

詳細文件：
- `CLAUDE.md` — 專案規則、工作流程、stack、deploy 相依
- `ARCHITECTURE.md` — 系統架構、資料流、storage layout、DB schema、pipeline 順序
- `ROADMAP.md` — phase 路線圖（v0.1 walking skeleton → v0.2 bundled pipeline → v0.3 adjustment panel → v1.0）
- `openspec/changes/` — 進行中的提案；`archive/` 是已 ship 的
- `docs/adr/` — Architecture Decision Records

### 本機開發（不用 Docker）

需要先有 PostgreSQL 16、Redis 7 在跑。

```bash
# Backend
pip install -e .
cp .env.example .env  # 編輯 DATABASE_URL / REDIS_URL / GEMINI_API_KEY
alembic upgrade head
uvicorn api.main:app --reload

# Worker（另開終端，吃 CPU 跑 NAFNet / YOLO）
python -m worker.main

# Frontend（另開終端）
cd web
npm install
npm run dev
```

## Tech stack

- Python 3.11 / FastAPI / SQLAlchemy 2.0 / Alembic / RQ
- AI / CV：PyTorch (CPU build) / NAFNet (inline) / Ultralytics YOLOv8 / OpenCV / Pillow / google-generativeai
- React 18 / Vite 5 / TypeScript 5 / Tailwind 3
- PostgreSQL 16 / Redis 7
- Docker Compose（api / worker / web / postgres / redis）

## Pipeline 順序

固定 `denoise → lens_distort → level_correct → auto_crop → color_grade`。每階段獨立 toggle；理由見 `ARCHITECTURE.md` § Pipeline 順序 與 `docs/adr/0002-bundled-v0.2.0-processing.md`。

## Manual Adjustments

`/preview` 目前支援點選任一照片後在上方 Before/After 載入該照片，並以同步 preview API 顯示手動調整結果。可對每張照片獨立點按向左/向右 90 度旋轉，並可調整曝光、對比、亮部、暗部、色溫、色偏、飽和、自然飽和、清晰度、銳利化與 HSL 六色區。水平旋轉、裁切縮放/偏移與手動變形修正集中在「構圖 / 幾何調整」視窗，使用者可即時看到裁切框與 live preview。每次滑桿/旋轉只會自動儲存該照片草稿；只有按「產生目前版本」或「產生已選版本」才會建立可下載的 `manual-vN` 版本，並更新 `processed_paths.adjusted` 指向最新版本。匯出 zip 時優先使用最新 `adjusted`，再 fallback 到 pipeline preset output，最後才用原圖。

已處理的單張照片可從照片卡片選擇不同版本下載：原圖、pipeline preset、手動 v1/v2/...。使用者 preset 存在 `adjustment_presets`，單張草稿參數存在 `photo_adjustments`，產生出的手動版本存在 `photo_adjustment_versions`。Manual adjustment 永遠從非 `adjusted` 的基準圖（pipeline output 或原圖）重新計算，不會把上一次 adjusted 結果當來源重複累加。手動水平、裁切、變形修正不會呼叫 Gemini AI。

## 對象使用者

最初為車輛刊登做批次後製，但工具本身是通用的批次照片後製。
