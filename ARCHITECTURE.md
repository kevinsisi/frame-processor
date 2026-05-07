# Architecture

照片批次後製工具的系統架構與資料流。

## 高層拓樸

```
┌─────────┐     ┌───────────┐     ┌───────────┐
│ web (R) │────▶│ api (FAS) │────▶│ postgres  │
│         │     │           │     └───────────┘
│         │     │           │     ┌───────────┐
│         │     │           │────▶│  redis    │◀──┐
└─────────┘     └─────┬─────┘     └───────────┘   │
                      │                           │
                      ▼                     ┌─────┴─────┐
                ┌──────────┐                │  worker   │
                │  storage │◀───────────────│   (RQ)    │
                │  (volume)│                └───────────┘
                └──────────┘
```

- **web**：React + Vite SPA。dev 用 Vite dev server；prod 用 nginx 起 static build。
- **api**：FastAPI（uvicorn）。負責上傳、查詢、enqueue 處理 job、串流檔案。
- **worker**：RQ Python worker。負責 zip 打包、之後的 AI 處理 pipeline。
- **postgres**：Project / Photo / Export 三張表（v0.2+ 加 ProcessingJob）。
- **redis**：RQ broker + result store。
- **storage**：Docker bind mount（dev `./data/`，prod `/mnt/usb/frame-processor/`）。原圖、預覽圖、處理後檔案、zip 都在這裡。

## 資料流（v0.1 walking skeleton）

### 上傳

```
FE ──POST /projects {name}──▶ API
                               ├─ INSERT Project
                               └─ return {id, name, ...}

FE ──POST /projects/{id}/photos (multipart)──▶ API
                                                ├─ for each file:
                                                │   ├─ save to <storage>/projects/{id}/originals/<photo_id>.<ext>
                                                │   └─ INSERT Photo
                                                └─ return [Photo, ...]
```

### 列表 / 預覽

```
FE ──GET /projects/{id}──▶ API ── SELECT Project + Photos ──▶ FE
FE ──GET /photos/{id}/file──▶ API ── stream file from disk ──▶ FE
```

### 匯出 zip

```
FE ──POST /projects/{id}/exports──▶ API
                                     ├─ INSERT Export (status=pending)
                                     ├─ rq.enqueue("worker.jobs.zip_export", export_id)
                                     └─ return {id, status: "pending"}

worker picks up job:
   ├─ load Export + Photos
   ├─ zip all originals to <storage>/exports/<export_id>.zip
   └─ UPDATE Export.status = "done", zip_path = ...

FE polls ──GET /exports/{id}──▶ API ── return {status, ...} ──▶ FE
FE ──GET /exports/{id}/download──▶ API ── stream zip ──▶ FE
```

## 儲存配置（Storage Layout）

```
<storage_root>/
├── projects/
│   └── {project_id}/
│       ├── originals/          # 原圖永不覆寫
│       │   ├── {photo_id}.jpg
│       │   ├── {photo_id}.png
│       │   └── ...
│       ├── thumbnails/         # 預覽縮圖（v0.2+，long edge 600px）
│       │   └── {photo_id}.webp
│       └── processed/          # 處理後輸出（v0.2+）
│           ├── {photo_id}.{preset_name}.jpg
│           └── ...
└── exports/
    └── {export_id}.zip
```

慣例：
- 原圖檔名一律用 `{photo_id}.<extension>`（保留原副檔名小寫），不保留使用者上傳檔名。原始檔名存到 `Photo.original_filename` 欄。
- 處理後檔名 `{photo_id}.{preset}.jpg`（永遠輸出 jpg quality=92）。
- zip 內部用 `Photo.original_filename` 還原使用者熟悉的檔名。

## DB Schema（v0.1）

### Project
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | |
| name | varchar(120) | 使用者輸入專案名稱（例：「BMW M3 2024-05-07 outdoor」） |
| created_at | timestamptz | |

### Photo
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK→Project | |
| original_filename | varchar(255) | 上傳時的檔名 |
| stored_path | varchar(512) | 相對 storage_root 路徑 |
| size_bytes | bigint | |
| width | int | 由 PIL 讀出 |
| height | int | 由 PIL 讀出 |
| mime_type | varchar(64) | |
| uploaded_at | timestamptz | |

### Export
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK→Project | |
| status | enum(pending, running, done, failed) | |
| zip_path | varchar(512) nullable | done 時才有 |
| error | text nullable | failed 時填寫 |
| created_at | timestamptz | |
| completed_at | timestamptz nullable | |

v0.2+ 會加 `ProcessingJob` 表記錄處理批次。

## 容器拓樸（dev）

`deploy/docker-compose.yml`：

| 服務 | 影像 | 暴露 port | 備註 |
|------|------|-----------|------|
| postgres | postgres:16-alpine | 5432 | dev 對外暴露方便接 DBeaver |
| redis | redis:7-alpine | 6379 | 同上 |
| api | 自 build | 8000 → 8000 | uvicorn `api.main:app` |
| worker | 自 build（共用 api Dockerfile） | — | `python -m worker.main` |
| web | 自 build（dev 是 vite dev；prod 是 nginx） | 5173 / 80 | |

prod 多接一層 reverse proxy（Cloudflare Tunnel 或 Caddy），參見部署 ADR（v1.0 寫）。

## CI/CD（v0.1）

`.github/workflows/ci.yml`：lint + 型別檢查 + 簡單 import smoke test。
`.github/workflows/deploy-dev.yml`：scaffold（v1.0 之前不接真實部署）。

## 後續演進指引

- v0.2 加 `services/photo_processor.py` 為 pipeline 主入口；單一 preset 是純 Pillow，可以在 worker 直接執行
- v0.3 加 NAFNet 需要 GPU runtime，docker-compose 會分出 `worker-cpu` 與 `worker-gpu`（參考 media-processor 的 multi-worker fan-out 模式）
- 大型 AI 模型權重路徑見 `models-weights/`（Docker volume），不入 git
