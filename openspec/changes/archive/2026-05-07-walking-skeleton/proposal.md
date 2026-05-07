# Walking Skeleton

**Status**: shipped — v0.1.0 scaffold 在 commit `c4a6677`、v0.1.1 UI 改版（romantic-cannon-38c856）、v0.1.2 production deploy 到 `https://frame.sisihome.org`（stupefied-mendel-e3664e）。已 archive。
**Date**: 2026-05-07
**Author**: Kevin

## Why

新建立的 frame-processor repo 是空的 GitHub template。在引入照片處理（NAFNet 降噪、自動裁剪、水平校正、色調預設）這些重量級 AI 依賴前，需要先把整條鏈拉出來：FastAPI → DB → 儲存 → React UI → RQ worker → zip 下載。

不先做這條 walking skeleton，第一個 AI feature 會被 stack 連線問題拖累；先驗收連線，AI 才有穩定地基。

## What Changes

提供「上傳 → 列表 → 下載 zip」的最小可用流程，**不含任何照片處理**：

- **Backend**：FastAPI app + 三個 router（projects / photos / exports）+ SQLAlchemy 2.0 ORM + Alembic 0001 migration（projects / photos / exports 表）+ Pydantic 2 schemas
- **Storage**：原圖落地慣例 `<storage>/projects/<pid>/originals/<photo_id>.<ext>`；EXIF orientation 由 PIL 處理
- **Worker**：RQ worker stub + `worker.jobs.zip_export_job`（唯一一個真正的 job）；之後的處理 pipeline job 會加在同個 worker
- **Frontend**：React 18 + Vite 5 + TypeScript 5 + Tailwind 3，三頁（Upload / Preview / Export）+ react-router 路由
- **Deploy**：docker-compose.yml 起五個服務（postgres / redis / api / worker / web）+ Dockerfile（api/worker 共用 image）+ nginx.conf（prod static 服務）
- **Docs**：CLAUDE.md（project 規則 + skill activation）、ARCHITECTURE.md（架構 + 資料流 + storage layout + DB schema）、ROADMAP.md（v0.1 → v1.0 路線圖）、README.md（quick start）
- **CI**：GitHub Actions ci.yml（Python ruff + import smoke + alembic offline migration check + 前端 typecheck + build）

## Non-Goals (defer)

- ❌ 照片處理（denoise / auto-crop / level / color grade）— v0.2.0+
- ❌ Auth / 登入 — v0.8.0
- ❌ Production 部署、HTTPS、reverse proxy — v1.0.0
- ❌ Thumbnail 生成 — v0.2.0（與處理 pipeline 一起）
- ❌ 處理進度即時 push（SSE / WebSocket）— 暫定 polling
- ❌ 一個檔案多個處理結果同時並排 — v0.2.0+

## Acceptance Criteria

- `docker compose up` 起來後，五個服務都健康
- `POST /projects` 建專案、`POST /projects/{id}/photos` multipart 上傳 N 張、`GET /projects/{id}` 看 photos 列表
- `GET /photos/{id}/file` 串流原圖（瀏覽器能直接顯示）
- `POST /projects/{id}/exports` 觸發 RQ job、`GET /exports/{id}` 看狀態、`GET /exports/{id}/download` 拿到 zip
- React UI 三頁能 navigate；上傳 → 預覽 → 匯出 → 下載完整流程能跑
- `alembic upgrade head` 在乾淨 DB 上能成功
- ruff + tsc 不報錯
