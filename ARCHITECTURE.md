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
- **storage**：Docker bind mount（prod `G:/frame-processor/storage-data`）。原圖、預覽圖、處理後檔案、zip 都在這裡。

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

## 資料流（v0.2 處理 pipeline）

### Thumbnail（lazy）

```
FE ──GET /photos/{id}/thumbnail──▶ API
                                    ├─ if cached webp exists → stream
                                    └─ else generate long-edge 600px webp
                                        → projects/<pid>/thumbnails/<photo_id>.webp
```

### 批次處理

```
FE ──POST /projects/{id}/process { preset, photo_ids?, level_correct, auto_crop_aspect }──▶ API
                                                                                              ├─ INSERT ProcessingJob (status=pending, total=N)
                                                                                              ├─ rq.enqueue("worker.jobs.processing_job", job_id, photo_id_strs)
                                                                                              └─ return ProcessingJob (202)

worker picks up job:
   ├─ UPDATE ProcessingJob.status = "running"
   ├─ for photo in target photos:
   │     ├─ pipeline: level_correct → auto_crop → color_grade
   │     ├─ save jpg to <storage>/projects/<pid>/processed/<photo_id>.<preset>.jpg
   │     ├─ UPDATE Photo.processed_paths[preset] = relative_path
   │     └─ UPDATE ProcessingJob.progress_done += 1
   └─ UPDATE ProcessingJob.status = "done" (or "failed" if all errored)

FE polls ──GET /processing-jobs/{id}──▶ API ── return {status, progress_done, progress_total, ...}
FE ──GET /photos/{id}/processed/{preset}──▶ API ── stream processed jpg ──▶ FE
```

### Pipeline 細節

```
原圖（PIL）
   ↓ ImageOps.exif_transpose（修正 iPhone / DJI 直拍 orientation）
   ↓ level_correct（Canny + HoughLinesP，|θ| ≤ 30° 中位數；超過 ±5° 不旋轉）
   ↓ auto_crop（Sobel energy + integral image sliding window；original 比例為 no-op）
   ↓ color_grade（依 preset 套白平衡 / 暖 / 冷 numpy float 運算）
   ↓ JPEG quality=92 寫入 processed/
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
│       └── processed/          # 處理後輸出（v0.2.0+）
│           ├── {photo_id}.{preset_name}.jpg
│           └── ...
├── models-weights/             # AI 模型權重（v0.2.0+，lazy download）
│   ├── ultralytics/
│   │   └── yolov8n.pt
│   └── nafnet/
│       └── NAFNet-SIDD-width32.pth
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

### ProcessingJob (v0.2.0)
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK→Project | |
| status | enum(pending, running, done, failed) | `processing_job_status` |
| preset | enum(showroom_white, outdoor_warm, night_cold) | `color_grade_preset` |
| denoise_strength | enum(none, light, medium, heavy) | NAFNet alpha-blend 強度 |
| lens_distort_correct | bool | 開廣角桶形矯正 |
| level_correct | bool | 開 Gemini 水平校正 |
| auto_crop_aspect | enum nullable | `aspect_ratio` 或 NULL = 跳過 crop |
| photo_ids | UUID[] | 處理的 photo id list |
| progress | int | 已完成張數 |
| total | int | 總張數 |
| error | text nullable | failed 時填寫 |
| created_at | timestamptz | |
| completed_at | timestamptz nullable | |

`Photo.processed_paths` (JSONB)：`{ "<preset_value>": "<storage-relative path>", ... }`

## Pipeline 順序

固定：`denoise → lens_distort → level_correct → auto_crop → color_grade`

1. denoise 最先 — geometric ops 會放大噪點
2. lens_distort 次之 — 廣角修平後 level/crop 才對得到真水平 / 真主體
3. level_correct 第三 — 用 Gemini Vision 估角度（無上限）+ `cv2.warpAffine`
4. auto_crop 第四 — YOLOv8n 偵測車輛 bbox + rule-of-thirds
5. color_grade 最後 — 純像素操作

## 處理資料流（v0.2.0）

```
FE ──POST /projects/{id}/process──▶ API
                                     ├─ INSERT ProcessingJob (status=pending)
                                     ├─ rq.enqueue("worker.jobs.process_photos_job", job_id, timeout=1800)
                                     └─ return {id, status: "pending"}

worker picks up job:
   ├─ load ProcessingJob + each Photo
   ├─ for each photo: denoise → lens → level → crop → grade
   │   └─ write <storage>/projects/<pid>/processed/<photo_id>.<preset>.jpg
   ├─ update Photo.processed_paths[preset_value]
   └─ UPDATE ProcessingJob.progress / status

FE polls ──GET /processing-jobs/{id}──▶ API ── return {status, progress, total}
FE ──GET /photos/{id}/file?variant=processed&preset=...──▶ API ── stream processed jpg
```

## 模型權重

- YOLOv8n：lazy download，Ultralytics 自動寫到 `ULTRALYTICS_DIR=/data/models-weights/ultralytics/`
- NAFNet-SIDD-width32：lazy download from HuggingFace mirror，寫到 `NAFNET_DIR=/data/models-weights/nafnet/NAFNet-SIDD-width32.pth`
- Gemini Vision：呼叫 Google AI Studio API，需 `GEMINI_API_KEY` env

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

## CI/CD（v0.3.10+）

`.github/workflows/ci.yml`：backend ruff + `python -m pytest tests` + import smoke + alembic offline check、frontend typecheck/build、api/web Docker build validation。

`.github/workflows/docker-publish.yml`：push `main` 或手動 dispatch 時 build/push `kevin950805/frame-processor-api:<commit-sha>`、`kevin950805/frame-processor-web:<commit-sha>`，並更新 `latest` alias。worker 服務重用 api image，僅用不同 command 啟動 RQ worker。

`.github/workflows/deploy-dev.yml`：Docker publish 成功後透過 Tailscale network + Windows OpenSSH Server 部署到 Windows desktop `100.83.112.20`。Workflow 會複製 `deploy/docker-compose.yml` 到 `D:/GitClone/_HomeProject/frame-processor/deploy/docker-compose.yml`，寫 host-side `deploy/.env` 的 commit SHA image tag，驗證 `G:/frame-processor/{postgres-data,storage-data,redis-data}` 皆存在且 compose/runtime mounts 都是 G 槽 bind mounts，再執行 `docker compose pull && docker compose up -d`，確認 runtime images 使用該 commit tag，並檢查 `http://100.83.112.20:8533/api/health` 回傳預期 app version。

## 後續演進指引

- v0.2 加 `services/photo_processor.py` 為 pipeline 主入口；單一 preset 是純 Pillow，可以在 worker 直接執行
- v0.3 加 NAFNet 需要 GPU runtime，docker-compose 會分出 `worker-cpu` 與 `worker-gpu`（參考 media-processor 的 multi-worker fan-out 模式）
- 大型 AI 模型權重路徑見 `models-weights/`（Docker volume），不入 git
