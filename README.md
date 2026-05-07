# frame-processor

照片批次後製工具。上傳 N 張 → 選風格 → 全部一鍵處理 → 下載 zip。

目前狀態：v0.1.0 walking skeleton（上傳 / 列表 / zip 匯出，**尚未含 AI 處理**）。

## Quick start

```bash
# 1. 起服務
cd deploy
docker compose up -d

# 2. 跑 alembic migration
docker compose exec api alembic upgrade head

# 3. 開瀏覽器
# Web UI:  http://localhost:5173
# API doc: http://localhost:8000/docs
```

## 開發

詳細文件：
- `CLAUDE.md` — 專案規則、工作流程、stack
- `ARCHITECTURE.md` — 系統架構、資料流、儲存配置、DB schema
- `ROADMAP.md` — phase 路線圖（v0.1 → v1.0）
- `openspec/changes/` — 進行中的提案

### 本機開發（不用 Docker）

需要先有 PostgreSQL 16、Redis 7 在跑。

```bash
# Backend
pip install -e .
cp .env.example .env  # 編輯 DATABASE_URL / REDIS_URL
alembic upgrade head
uvicorn api.main:app --reload

# Worker（另開終端）
python -m worker.main

# Frontend（另開終端）
cd web
npm install
npm run dev
```

## Tech stack

- Python 3.11 / FastAPI / SQLAlchemy 2.0 / Alembic / RQ
- React 18 / Vite 5 / TypeScript 5 / Tailwind 3
- PostgreSQL 16 / Redis 7
- Docker Compose

## 對象使用者

晴晴（攝影師）。為 carsmeet.tw 與 8891 車輛刊登做批次後製。
