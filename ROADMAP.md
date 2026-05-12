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
- **v0.1.2** — Production deploy 到 `https://frame.sisihome.org`（合併 `claude/stupefied-mendel-e3664e`）：docker-compose 對外只開 web container（最初 8533，v0.3.24 起改 18533 避開 Windows excluded port ranges）、nginx `/api/*` reverse proxy 到 `api:8000`、`VITE_API_BASE_URL=/api`、API `ALLOWED_ORIGINS` 含 frame.sisihome.org、RPi Caddy `request_body.max_size 500MB`。alembic 0001 修小問題，web 加 `@types/node`。

對應提案：`openspec/changes/archive/2026-05-07-walking-skeleton/`（已 archive）

---

## v0.2.0 — Bundled Processing Pipeline ✅ (shipped)

**目標**：第一個真正能用的處理工具。把原 ROADMAP v0.2 + v0.3 + v0.4 + v0.5 一次到位，外加廣角畸變矯正。

範圍：
- `services/color_grade.py` 三組 Pillow preset（`SHOWROOM_WHITE` / `OUTDOOR_WARM` / `NIGHT_COLD`）
- `services/denoise.py` NAFNet-SIDD-width32 inline 架構 + lazy weight download；`DenoiseStrength` 輕/中/重 透過 alpha-blend 控制
- `services/lens_distort.py` OpenCV `cv2.undistort` 桶形畸變矯正（中度廣角預設係數）
- `services/level_correct.py` **Gemini Vision** 估角度（不是 Hough line）+ `cv2.warpAffine` 旋轉，無上限
- `services/auto_crop.py` Ultralytics YOLOv8n 偵測車輛 + rule-of-thirds 構圖；6 個目標比例（原始 / 3:2 / 4:3 / 16:9 / 1:1 / 9:16）
- `services/photo_processor.py` orchestrator，v0.2.0 初版順序：denoise → lens → level → crop → grade（v0.4.x 擴充為 `denoise → chroma_clean → detail_preserve → lens_distort → level_correct → auto_crop → cpl_look → color_grade`，見下方子版本與 ARCHITECTURE.md § Pipeline 順序）
- `models/enums.py` `ColorGradePreset` / `AspectRatio` / `DenoiseStrength` / `ProcessingJobStatus`
- `models/processing_job.py` 新表；`Photo.processed_paths` JSONB column
- `POST /projects/{id}/process` body `{preset, denoise_strength, lens_distort_correct, level_correct, auto_crop_aspect, photo_ids?}`
- `GET /processing-jobs/{id}` 查 status + progress
- `GET /photos/{id}/file?variant=processed&preset=...`
- worker `process_photos_job` + `zip_export_job` 改成優先打包處理後檔案
- alembic 0002 建 enums + processing_jobs + photos.processed_paths
- Docker：API 使用 CPU-only torch wheel；batch worker 使用 CUDA torch wheel + GPU runtime；libgl + Gemini key env + 模型權重 volume mount
- FE：`PipelinePanel` (preset / denoise 強度 / lens 開關 / level 開關 / aspect) + 進度條 polling + `BeforeAfter` 拖拉對比

非範圍（defer）：
- 自訂 preset / 自訂裁剪框微調 — v0.7+
- 處理進度即時 push (SSE/WebSocket) — 仍 polling
- 多 preset 平行輸出

對應提案：`openspec/changes/archive/2026-05-07-v0.2.0-processing-pipeline/`（已 archive）

子版本：
- **v0.2.0** — bundled pipeline ship（commit `5e7fc80` → merge `791e851` → cleanup `208c9b9`）
- **v0.2.1** — post-ship FE 修正：per-photo queue progress（job 列出每張 done/running/queued 狀態）、AppFooter 拿掉 carsmeet/8891 字眼
- **v0.2.2** — 設定頁 + Gemini API key 匯入：DB-backed runtime key pool、env fallback；key-manager trusted-only 同步只在後端明確設定 `KEY_MANAGER_URL` 時作為可選捷徑，供水平校正使用

---

## v0.3.0 — Lightroom-style Adjustment Panel

**目標**：preset + auto pipeline 解決 80% 場景；剩下 20% 需要手動微調 sliders。

範圍（第一版已部署，持續收斂）：
- `services/adjustments.py`：每張照片獨立 90 度 orientation 旋轉 / 手動水平 / 裁切縮放與偏移 / 手動變形修正 / 曝光 / 對比 / 亮部 / 暗部 / 色溫 / 色偏 / 飽和 / 自然飽和 / 清晰度 / 銳利化 / HSL × 6 色
- `photo_adjustments` 保存草稿；`photo_adjustment_versions` 保存使用者按「產生」後的手動版本，照片卡片版本下拉會切換卡片圖、Before/After 基準、調整來源與下載目標
- 幾何操作走全螢幕單圖構圖工作區，顯示水平比對格線、可拖曳裁切框並提供取消/完成
- `models/adjustment_preset.py` + `models/photo_adjustment.py` + alembic `0004_adjustment_panel`
- API：`POST /photos/{id}/adjustments`、`POST /photos/{id}/preview` (live 同步)、`POST /projects/{id}/adjustments/apply` worker batch、preset CRUD
- FE：`AdjustmentPanel` + 即時 preview slider + preset save/load/delete + 點照片同步上方 Before/After + 單張 processed download
- Preview：小圖先縮再套手動調整，旋轉/色溫在手機上需即時且肉眼可見；完整解析度只在產生版本時 render
- Export zip 優先 `processed_paths.adjusted` → preset processed → original
- 待辦：iPhone Safari mobile QA、降噪可視化/preview 比較強化、更多細節控制校準

對應提案：`openspec/changes/2026-05-07-v0.3.0-adjustment-panel/`

子版本（app version 0.3.0–0.3.29，皆已 ship；版號定義見「版本號碼說明」）：
- **0.3.x（FE 主導）** — adjustment panel 收斂：generated `manual-vN` 版本獨立於 draft、live preview 縮圖速度修正、全螢幕構圖工作區、手動水平/垂直透視拆分、版本下拉同步 Before/After 與下載目標、預設 medium 降噪/lens on/level on、iPhone Safari 預覽即時感、強化 medium / heavy 降噪 edge-aware blend、低光肖像 regression 修正、自動 batch 補產缺漏版本、Upload→Preview pipeline 設定串接、sticky 開始產生列、Before/After 切換上一張/下一張、preview-ux-audit 文件。
- **0.3.25** — chore: app + deploy health gate 對齊到 0.3.25，讓 desktop runner 可驗證 runtime app version。

---

## v0.4.0 — AI Batch Versioning & Quality ✅ (shipped)

**目標**：把單次 batch 變成可回看 / 重試 / 隱藏 / 指定下載的「AI 版本」概念，並補上反光/偽色/細節保留三個 batch step 與 GPU worker，讓批次輸出在品質與可重現性上都不再黑盒。

範圍（已 ship）：
- AI 批次版本：每次按「開始產生」建立 `AI vN`，輸出落在 immutable `batch-vN/`；`processing_jobs.version_number` / `archived_at` / retry metadata + 新表 `photo_processing_versions` 紀錄逐張狀態；`processed_paths[preset]` 退化為「最新成功且未封存版本」的相容 cache。
- 重試流程：完整重試（建立同 selection 新版本）+ retry-missing-only（明確標記 partial）；failed/partial 版本 expose error 不會 silent fallback。
- Export 指定版本下載；archive/hide 已完成或失敗的版本；orphaned successful version 防呆。
- `services/chroma_clean.py` 偽色雜色修正（low/medium/high）—只壓暗部 chroma，保護黃色安全帶 / Logo / 氛圍燈，亮度細節不動。
- `services/detail_preserve.py` luma-only 高頻回填，把原圖可信亮度紋理塞回降噪後輸出，不 hallucinate、不回填 chroma noise。
- `services/cpl_look.py` 車內 CPL 反光抑制 look（low/medium/high）—鏡面飾板、儀表玻璃、中控螢幕、車窗反光；拍後 anti-glare，不是玻璃場景分離也不還原白爆。
- Pipeline 順序擴充：`denoise → chroma_clean → detail_preserve → lens_distort → level_correct → auto_crop → cpl_look → color_grade`（ARCHITECTURE.md § Pipeline 順序）。
- AI 處理 per-photo queue：批次建立時逐張寫入 `pending` 並 enqueue，worker 單張完成後回算父版本進度；Preview 在 running 期顯示「處理中 / 待處理」而非誤報缺漏。
- Downloaded version mark：照片卡片下載過任一版本後以瀏覽器本機儲存標示「已下載」，重整後仍保留。
- Preview 不再因預設 pipeline identity 變更把已有 AI 版本的舊專案整批重跑（`23cf20c`）。
- **GPU worker split**：AI batch worker 拆為獨立 CUDA PyTorch image（共用 `deploy/api.Dockerfile` + `TORCH_WHEEL_INDEX=cu126` build arg），API image 仍 CPU，`deploy/docker-compose.yml` worker service 配 `gpus: all`，部署驗證 worker 內 `torch.cuda.is_available()` 為 true 才算成功；workflow secret 與 G 槽 mount 驗證見 README § CI/CD。
- 文件：lens / Gemini level correction 在 README 與 CLAUDE.md 標註為可選幾何步驟，預先校正過的照片可單跑 AI 降噪不被強制套幾何。

非範圍（defer）：
- 多 preset 平行 batch — v0.6 preset bundle 才處理
- 即時 push 進度（SSE/WebSocket）— 仍 polling
- 自訂 preset — v0.7
- Reflection Removal 玻璃場景分離 / 還原白爆細節 — 非本 phase 範疇

對應提案：
- `openspec/changes/2026-05-10-batch-version-control/`（39/42，剩 backend 測試）
- `openspec/changes/2026-05-11-car-interior-cpl-look/`（8/8，可 archive）
- `openspec/changes/add-frame-ci-cd/`（15/16，剩 GPU worker 部署驗證）
- Chroma Clean / Detail Preserve / per-photo queue / downloaded mark / GPU worker split 走 commit-level，未開獨立 OpenSpec。

子版本（web/package.json + api/main.py + web/src/version.ts 同步）：
- **0.4.0** — AI Batch Version Control 首發（commit `3eba8e3`）
- **0.4.1** — fix: restore project preview loading（`bd20fbb`）
- **0.4.2** — 車內 CPL Look batch step（`b12caf6`）
- **0.4.3** — fix: 手機 preview pipeline 控制穩定（`8d899f4`）
- **0.4.4** — Chroma Clean false-color cleanup batch step（`f7b6e97`）
- **0.4.5** — Downloaded version 卡片標示 + 本機儲存（`8455571`）
- **0.4.6** — AI 批次 per-photo queue 進度（`f160c75`）
- **0.4.7** — Detail Preserve 細節保留 batch step（`11b3849`）
- **0.4.8** — fix: 避免預設 pipeline identity 改變導致舊 AI 輸出被重跑（`23cf20c`）
- **0.4.9** — GPU worker split：worker CUDA image、`docker compose` 掛 GPU、deploy 驗證 `torch.cuda.is_available()`、geometry 校正文件改寫（`1e7a38a` + `293e61e`）

---

## v0.3 / v0.4 / v0.5（原計畫的 NAFNet / YOLO crop / Hough level）— merged into v0.2.0 ✅

原 ROADMAP 把 NAFNet 降噪（v0.3）、自動裁剪（v0.4）、水平校正（v0.5）拆三個 release。實際走完 v0.1 後重評估，分四次發佈對使用者沒意義（半成品 demo），全部合併到 v0.2.0。新 v0.3.0 變成 adjustment panel，新 v0.4.0 變成 AI Batch Versioning & Quality（上方兩個段落）。

`ARCHITECTURE.md` § Pipeline 順序與 `docs/adr/0002-bundled-v0.2.0-processing.md` 記錄理由。

---

## v0.6.0 — Preset Bundle UI

v0.2.0 已經把 pipeline 串完，v0.6 處理「使用體驗」層：

範圍：
- 一鍵套用 preset bundle（例如「展示間白完整版」= 降噪中 + 廣角矯正 + 水平校正 + 裁剪 4:3 + 色調白）
- FE 提供 3 個預設 bundle + 自訂進階模式
- 處理進度顯示每階段細項（denoise xxx / lens xxx / level xxx ...）

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

### 版本號碼說明

App version 是單一 canonical 值，必須在以下四處同步 bump：

1. `api/main.py` `APP_VERSION` — `/health` 與 FastAPI title 用
2. `web/src/version.ts` `APP_VERSION` — 前端顯示用
3. `web/package.json` `version` — npm 套件 metadata
4. `.github/workflows/deploy-dev.yml` `EXPECTED_APP_VERSION` — CD 部署後的 health gate

`pyproject.toml` 的 `version` 是 Python 套件 metadata，目前慣例與上面四處同步。歷史上 v0.4.x 系列曾漏 bump pyproject，已於 v0.4.9 之後對齊；之後每次發版請四處 + pyproject 一起改。
