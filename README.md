# frame-processor

照片批次後製工具。上傳 N 張 → 選 preset + 處理選項 → 全部一鍵處理 → 下載 zip。

目前狀態：**v0.2.1 — bundled processing pipeline shipped**（NAFNet AI 降噪 / 廣角畸變矯正 / Gemini Vision 水平校正 / YOLOv8 自動裁剪 / Pillow 色調 preset / before-after 對比 / per-photo queue progress）。已部署至 [frame.sisihome.org](https://frame.sisihome.org)。

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

`deploy/docker-compose.yml` 從同目錄 `.env` 讀取（或主機 env 直接 inject）：

```bash
GEMINI_API_KEY=xxx          # 水平校正必要（Gemini Vision 估角度）；缺則 level_correct 會 fail
GEMINI_MODEL=gemini-2.0-flash   # 預設值
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

## 對象使用者

最初為車輛刊登做批次後製，但工具本身是通用的批次照片後製。
