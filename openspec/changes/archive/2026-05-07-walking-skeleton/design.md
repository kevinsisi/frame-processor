# Walking Skeleton — Design Notes

## 為何選這個 layout（api/ services/ models/ worker/ web/ 平鋪）

對比 media-processor 的 `src/media_processor/...` 套件式結構，這個專案目前的 scope 較小，平鋪比較容易讀，import path 也短（`from models.photo import Photo`）。

進入 v0.6+（多 worker、GPU/CPU 分流）後若需要重組，再 migrate 到 `src/frame_processor/...` 模式。

## 為何選 RQ 而不是 Celery / Dramatiq

- RQ 對小型專案足夠，文件少、上手快
- media-processor 已在用 RQ，運維經驗可以直接複用
- 之後若要分多 queue（`processing` / `export` / `gpu-only`），RQ 直接支援

## 為何 worker 與 api 共用 image

walking skeleton 階段兩者依賴幾乎相同（FastAPI 依賴對 worker 多餘但無害），共用 image 減少建置時間與 registry 大小。

到 v0.3.0 引入 PyTorch + NAFNet 後，worker image 會加大（~3GB）。屆時：
- 拆出 `deploy/api.Dockerfile`（只裝 web 框架）+ `deploy/worker.Dockerfile`（裝 ML 依賴）
- 或 multi-stage build 共用 base layer

## 為何 zip 透過 worker 而不是 FastAPI handler 直接打包

雖然 v0.1 的 zip 只是檔案複製，理論上可以同步在 handler 內做。但：

1. 驗證 worker 整條鏈通了（API → enqueue → worker pick → DB update → polling）
2. 大量照片（>100 張）打包可能需要數十秒，handler 同步會 block
3. v0.2+ 處理 pipeline job 會走同個 worker，先建立模式

## 為何 storage 用 docker volume 而不是 bind mount

dev 階段用 named volume 簡單，跨 OS 一致。Prod 部署到 Pi 時改用 bind mount 對到 `/mnt/usb/frame-processor`（與 carsmeet 的儲存習慣一致）。

## 為何 PostgreSQL 而不是 SQLite

- 與 media-processor / sheet-to-car 一致，運維經驗共用
- alembic migration 在 PostgreSQL 上的 ENUM 行為是 well-defined（SQLite 沒 ENUM 要 emulate）
- 多 worker 並寫 Photo 列時不會被 SQLite locking 卡住

## 沒有做的事

- **沒寫 thumbnails**：原圖直接給 `<img>` 顯示。50 張 5MB 照片 = 250MB 同時下載；如果 dev 機房路況好就無感。v0.2 加 thumbnail 一起做。
- **沒處理 HEIC/HEIF**：Pillow 預設不支援 HEIC，需要 `pillow-heif`。先標記在 `SUPPORTED_EXTENSIONS` 但實際上傳 HEIC 會在讀尺寸時 silently fail（width/height 變 None，檔案還是存得起來）。v0.2 修。
- **沒寫 tests**：`pytest` 在 dev deps 內、`tests/` 目錄空的。v0.2 加第一輪 backend/frontend 測試。
- **沒做 frontend 錯誤邊界**：fetch 失敗就直接 setError；沒做 toast / retry。

## 未來注意點

- **Photo.id 用 UUID**：之後若引入 multi-tenant、外部分享 link，UUID 比 auto-increment 安全
- **Export.zip_path 是 relative path**：永遠相對 `STORAGE_ROOT`；換 deployment 環境只要改 `STORAGE_ROOT` 不用搬資料庫欄位
- **RQ job 用 string path**：`"worker.jobs.zip_export_job"`；任何 rename 都要同步改 router 與 worker（用 enum 集中管理是 v0.6+ 的 hardening 任務）
