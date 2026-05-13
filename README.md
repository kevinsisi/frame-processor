# frame-processor

照片批次後製工具。上傳 N 張 → 選 preset + 處理選項 → 全部一鍵處理 → 下載 zip。

目前狀態：**v0.4.14 — showroom white contrast + gradient smoothing**（`showroom_white` 內建等同手動對比 +55 的 luma-only 對比提升，並對平滑低彩車身面加入極輕微 luma dither、提高 JPEG 輸出品質，降低大面積同色區色階斷層；沿用 v0.4.13 denoise dark mesh guard、v0.4.12 Chroma Clean dark mesh de-moire、安全幾何預設、GPU worker、ZIP 最新 AI 版本匯出與 Detail Preserve）。正式環境：[frame.sisihome.org](https://frame.sisihome.org)。

## Quick start

```bash
# 1. 起服務
cd deploy
docker compose up -d --build

# 2. 開瀏覽器
# Web UI:  https://frame.sisihome.org   （或本機 http://localhost:18533 / dev http://localhost:5173）
# API doc: 經 nginx → /api/docs
```

> alembic migration 由 api container 啟動時自動跑（`alembic upgrade head` 寫死在 entrypoint）。

> Production on `kevinhome` stores persistent Docker data under `G:\frame-processor\` (`postgres-data`, `storage-data`, `redis-data`) to avoid filling the C drive.
> For migration or disaster recovery, create these directories first and copy the existing Docker volume contents into them before starting the stack; starting with empty directories creates an empty PostgreSQL/storage state.

### 版本號碼

App version 是單一 canonical 值，發版時必須在這五處同步 bump：

1. `api/main.py` `APP_VERSION` — `/health` 與 FastAPI title
2. `web/src/version.ts` `APP_VERSION` — 前端顯示
3. `web/package.json` `version` — npm 套件 metadata
4. `.github/workflows/deploy-dev.yml` `EXPECTED_APP_VERSION` — CD 部署後 health gate
5. `pyproject.toml` `version` — Python 套件 metadata

v0.4.x 系列曾漏 bump `pyproject.toml`，已於 v0.4.9 後對齊；之後每次發版五處一起改。版號定義與子版本對應見 `ROADMAP.md`。

### 必要環境變數

`deploy/docker-compose.yml` 從同目錄 `deploy/.env` 讀取（或主機 env 直接 inject）：

```bash
GEMINI_API_KEY=xxx          # 可選 fallback；DB key pool 優先，兩者都缺才會讓 level_correct fail
GEMINI_MODEL=gemini-2.5-flash   # 預設值
SETTINGS_ADMIN_TOKEN=xxx    # /settings 修改金鑰必要；只用於 PUT/DELETE/sync mutation
KEY_MANAGER_URL=            # 可選；空白代表不啟用 key-manager 同步，直接貼 key 即可
ULTRALYTICS_DIR=/data/models-weights/ultralytics  # YOLOv8 權重 cache
NAFNET_DIR=/data/models-weights/nafnet            # NAFNet 權重 cache
```

模型權重（YOLOv8n 6MB + NAFNet-SIDD-width32 ~112MB）首次處理時 lazy download 到對應 volume 路徑，之後跨 container restart 共用。

### 幾何校正注意

廣角畸變矯正與 Gemini 水平校正都是幾何變形步驟，不是降噪步驟。若照片已被手機/相機或前期流程校正，或同一批混有不同鏡頭、不同裁切比例，請關閉「廣角畸變矯正」；若處理後仍出現不合理旋轉或拉伸，也關閉「Gemini 水平校正」後重跑一版。AI 降噪、Chroma Clean、Detail Preserve 可以獨立保留，不需要為了降噪強制套幾何校正。

## CI/CD Deployment

GitHub Actions 使用 HomeProject two-workflow pattern：

- `.github/workflows/docker-publish.yml`：push `main` 或手動 dispatch 時 build/push `kevin950805/frame-processor-api:<commit-sha>`、`kevin950805/frame-processor-worker:<commit-sha>`、`kevin950805/frame-processor-web:<commit-sha>`，並更新 `latest` alias；API image 使用 CPU torch，worker image 使用 CUDA torch。
- `.github/workflows/deploy-dev.yml`：Docker publish 成功後跑在 kevinhome GitHub self-hosted runner `DESK-KEVINHOME-frame-processor`（labels: `self-hosted`, `Windows`, `X64`, `frame-processor-prod`），直接在 Windows desktop `100.83.112.20` 本機部署。Workflow 會複製 `deploy/docker-compose.yml` 到 `D:/GitClone/_HomeProject/frame-processor/deploy/docker-compose.yml`，merge host-side `deploy/.env` 的 commit SHA image tag 與 runtime secrets，再用 GitHub `DOCKERHUB_TOKEN` 產生臨時 Docker auth config 逐一 `docker pull` postgres、redis、api、worker、web images，最後以 `docker compose up -d --pull never --no-build` 套用；部署後會確認 worker 使用 dedicated worker image 且 container 內 `torch.cuda.is_available()` 為 true。臨時 auth config 會在 cleanup 中刪除。Production web host port 使用 `18533`，避開 Windows/Hyper-V reboot 後常見的 `85xx/86xx` excluded port ranges；API 不 publish host debug port，前端 nginx 透過 Docker network 反向代理到 `api:8000`。

部署前 workflow 會拒絕缺少 `G:/frame-processor/postgres-data`、`G:/frame-processor/storage-data`、`G:/frame-processor/redis-data` 的主機，也會用 `docker compose config` 確認 postgres/storage/redis 都是 G 槽 bind mounts。部署後會用 `docker inspect` 再確認 runtime images 使用該 commit tag 且 mounts 沒有回到 Docker Desktop C 槽 named volumes，最後檢查 `http://100.83.112.20:18533/api/health` 回傳預期 app version。

必要 GitHub secrets：`DOCKERHUB_TOKEN`。`DOCKERHUB_USERNAME` 可省略，預設 `kevin950805`。`GEMINI_API_KEY`、`SETTINGS_ADMIN_TOKEN`、`KEY_MANAGER_URL` 可由 GitHub secrets 提供；若未提供，workflow 會保留桌機既有 `deploy/.env` 值而不是寫入空字串。`GEMINI_API_KEY` 只是 runtime fallback，DB key pool 才是優先來源；CD 不因缺少 fallback key 而阻擋部署。`SETTINGS_ADMIN_TOKEN` merge 後仍必須存在，且只進 api/worker runtime env，不 bake 進 static web image；Settings 頁需要修改金鑰時可手動輸入 token。`KEY_MANAGER_URL` 是 optional；空白代表不啟用 key-manager sync。`GEMINI_MODEL` 由 workflow 固定為 `gemini-2.5-flash`。Runner helper 位於 `D:/GitClone/_HomeProject/_github-runner-frame-processor/start-runner.ps1`，登入自啟腳本位於 Windows Startup folder 的 `frame-processor-runner-autostart.cmd`。

## 開發

詳細文件：
- `CLAUDE.md` — 專案規則、工作流程、stack、deploy 相依
- `ARCHITECTURE.md` — 系統架構、資料流、storage layout、DB schema、pipeline 順序
- `ROADMAP.md` — phase 路線圖（v0.1 walking skeleton → v0.2 bundled pipeline → v0.3 adjustment panel → v1.0）
- `docs/preview-ux-audit.md` — Preview 頁 UX 分析、優先改善計畫與未關閉 QA
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

固定 `denoise → chroma_clean → detail_preserve → lens_distort → level_correct → auto_crop → cpl_look → color_grade`。每階段獨立 toggle；理由見 `ARCHITECTURE.md` § Pipeline 順序 與 `docs/adr/0002-bundled-v0.2.0-processing.md`。

## Manual Adjustments

`/preview` 目前支援點選任一照片後在上方 Before/After 載入該照片，也可直接在 Before/After 比較圖左右箭頭切換上一張/下一張，並以同步 preview API 顯示手動調整結果。Preview API 會先縮成小圖再套用手動旋轉、幾何與色彩，避免手機大圖每次旋轉/色溫調整卡數十秒；AI 降噪、廣角矯正與 Gemini 水平校正屬於 batch pipeline，不會在尚未產生的微調 preview 內假裝完成。若目前照片仍是原圖且沒有批次處理版本，Preview 頁會依目前處理設定自動背景建立 batch job；Before 永遠保持未降噪原圖，After 在完成後自動切到處理後版本，才能直接看出降噪差異。Upload 頁選擇的色調風格會寫入專案 pipeline 設定，Preview 的處理面板、固定底部開始產生列與自動 batch job 都使用同一份 state；pending/running job 會停用產生按鈕與 pipeline 設定，避免重複建立 job。照片卡片的版本下拉會切換卡片圖片、上方 Before/After 後側來源、後續手動調整來源與單張下載目標；未手動指定版本時預設以原圖作為 live preview 來源，批次處理完成後會自動切到剛產生的 preset 版本，避免誤看舊 processed output。可對每張照片獨立點按向左/向右 90 度旋轉，並可調整曝光、對比、亮部、暗部、色溫、色偏、飽和、自然飽和、清晰度、銳利化與 HSL 六色區。水平旋轉、裁切縮放/偏移與手動水平/垂直透視修正集中在全螢幕單圖「構圖 / 幾何調整」工作區，裁切框與格線只覆蓋實際圖片而不是黑邊容器，使用者可拖曳裁切框本體、用邊角 handles 固定比例縮放，並在預覽圖上即時看到水平校正與透視變形；取消/完成控制是否套用。每次滑桿/旋轉只會自動儲存該照片草稿；只有按「產生目前版本」或「產生已選版本」才會建立可下載的 `manual-vN` 版本，並更新 `processed_paths.adjusted` 指向最新版本。匯出 zip 時優先使用最新 `adjusted`，再 fallback 到 pipeline preset output，最後才用原圖。

已處理的單張照片可從照片卡片選擇不同版本：原圖、immutable AI v1/v2/...、legacy 批次 preset、手動 v1/v2/...。AI 批次版本存在 `processing_jobs` + `photo_processing_versions`；`processed_paths[preset]` 只保留最新成功且未封存版本的相容 cache。使用者 preset 存在 `adjustment_presets`，單張草稿參數存在 `photo_adjustments`，產生出的手動版本存在 `photo_adjustment_versions`。未明確選版本時，manual adjustment 避免使用內部 `adjusted latest` 當來源；若使用者明確在下拉選單選手動或 AI 版本，該版本會成為後續微調來源。匯出 ZIP 的預設路徑順序為 `adjusted` → 最新完成且未封存的 AI 版本 → 相容 cache 內任一 processed path → 原圖；指定 `processing_job_id` 時則只匯出該 AI 版本的完成輸出。手動水平、裁切、水平/垂直透視修正不會呼叫 Gemini AI。批次 pipeline 預設為中度 AI 降噪、中度 Chroma Clean 偽色雜色修正、輕度 Detail Preserve 細節保留、廣角畸變矯正關閉、Gemini Vision 水平校正關閉、自動裁剪維持原圖比例、CPL Look 關閉；Chroma Clean 只處理暗部 chroma 以壓低紅綠紫色斑與彩色顆粒，保護黃色安全帶、Logo 與氛圍燈；Detail Preserve 只回填原圖可信亮度紋理，不生成或補畫車況細節，也不把彩色噪點加回來；CPL Look 可針對汽車內裝黑色亮面飾板、儀表玻璃、中控螢幕與車窗反光做拍後反光抑制。v0.3.29 起 NAFNet 權重改從官方 Google Drive 下載，避免 production 因 HuggingFace 401 長期落到 fallback。中度降噪在 NAFNet 太保守或權重不可用時會用更明顯的 OpenCV 強化 pass，但不再做後段 unsharp，以免平坦區噪點被再次銳化；重度降噪保留給明確需要更強暗部清噪的情境，且不可為了平滑而全圖抹成油畫。medium/heavy 都使用 edge-aware blend 讓天空、牆面、暗部等平坦區域清噪，同時保護建築線條、窗框與車身邊緣；heavy 後仍做 thresholded unsharp mask 細節補償。廣角矯正不再只做固定弱桶形係數，也會偵測左右側近垂直線是否向上收斂，若有則套用自動垂直透視矯正。

## 對象使用者

最初為車輛刊登做批次後製，但工具本身是通用的批次照片後製。
