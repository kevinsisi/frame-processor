# ROADMAP

照片批次後製工具的路線圖。版本號採語意化版本（major.minor.patch）。

每個 phase 都有對應的 `openspec/changes/<change-id>/` 提案；提案 archive 後填入「狀態 / 對應提案」連結。

## Active OpenSpec changes（含 backlog）

進行中：

- `2026-05-07-v0.3.0-adjustment-panel` — 主功能 ship，剩 iPhone Safari mobile QA / showroom_white smoke / 單張下載驗證。
- `2026-05-10-batch-version-control` — feature 完成；integration tests 標 deferred，待 `add-frame-test-harness` 解。
- `add-frame-ci-cd` — implementation complete; ready to archive after final spec sync.

Backlog（已寫 spec，未開工）：

- `add-frame-test-harness` — backend 整合測試 harness（testcontainers Postgres + TestClient + fake RQ）。解 batch-version-control 的 deferred verification + 後續整合測試需求。**優先**。
- `add-frame-eslint-v9-migration` — v0.4.10 已加最小 flat config 讓 `npm run lint` 可執行；仍需補 type-aware / recommended / react-refresh 規則與 CI lint step。
- `add-frame-pipeline-step-docs` — ARCHITECTURE.md 補 chroma_clean / detail_preserve / cpl_look 三節對齊既有 service。
- `add-frame-error-reporting-frontend` — Preview.tsx 5 個 console.warn 換成 user-visible toast + 共用 errorReporting util。
- `add-frame-job-timeout-config` — RQ `job_timeout=1800` 寫死的兩處拉到 settings + per-photo budget 文件化。**依賴** `add-frame-test-harness` 才能測。
- `add-frame-processed-paths-typing` — `processed_paths: dict[str, str]` 收緊到 `ColorGradePreset` key + validator + 統一 writer helper。

未來 phase（ROADMAP 段落已述，OpenSpec 開工時才建檔）：

- v0.6.0 — Preset Bundle UI
- v0.7.0 — 自訂 preset
- v0.8.0 — 認證 + 8891 整合
- v1.0.0 — Production Ready（HTTPS / 監控 / 備份 / carsmeet 入口）

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
- **0.3.x（FE 主導）** — adjustment panel 收斂：generated `manual-vN` 版本獨立於 draft、live preview 縮圖速度修正、全螢幕構圖工作區、手動水平/垂直透視拆分、版本下拉同步 Before/After 與下載目標、預設 medium 降噪、iPhone Safari 預覽即時感、強化 medium / heavy 降噪 edge-aware blend、低光肖像 regression 修正、自動 batch 補產缺漏版本、Upload→Preview pipeline 設定串接、sticky 開始產生列、Before/After 切換上一張/下一張、preview-ux-audit 文件。
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
- `openspec/changes/2026-05-10-batch-version-control/`（feature 完成；integration tests deferred 到 `add-frame-test-harness`）
- `openspec/changes/archive/2026-05-11-car-interior-cpl-look/`（已 archive）
- `openspec/changes/add-frame-ci-cd/`（15/16，剩 GPU worker 部署驗證）
- Chroma Clean / Detail Preserve / per-photo queue / downloaded mark / GPU worker split 走 commit-level，未開獨立 OpenSpec。

對應 ADR：
- `docs/adr/0003-batch-versioning.md` — immutable `batch-vN` 路徑 + archive 語意 + project-scoped version 編號的選擇理由
- `docs/adr/0004-gpu-worker-split.md` — AI worker 拆 CUDA image，沒 GPU 直接 fail 不降級（量化 CPU 8-12 min vs GPU < 90s）

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
- **0.4.10** — safe geometry defaults + export/detail hotfixes：Preview 預設關閉 lens/Gemini level 幾何校正，只保留 AI denoise/chroma/detail；Gemini 回傳超出範圍角度時跳過旋轉，不讓整批失敗；ZIP 相容匯出會在 cache 為空時查最新完成 AI 版本；NAFNet tile feather、Detail Preserve source-structure 回補與 `showroom_white` Lightroom `01.CH偏光色` 方向調整，修正 911 專案 logo/輪框細節流失與格狀 artifact 風險。
- **0.4.11** — dark chroma de-grid + neutral showroom white：denoise / Chroma Clean 對暗部低彩平坦區做 luma-safe chroma de-grid，壓低黑牆、玻璃與暗部的彩色棋盤格 artifact；`showroom_white` 改為中性偏冷白，並將 clarity 改成只銳化亮度，避免 RGB unsharp 放大暗部 chroma pattern。
- **0.4.12** — dark mesh de-moire：Chroma Clean 中度新增暗部低彩/低變化 mesh pass，在受保護 mask 內同時壓低 luma 與 chroma 細密網格，並避免處理文字、車標、紅色物件與大面積飽和氛圍燈。
- **0.4.13** — denoise dark mesh guard：修正 NAFNet/OpenCV medium denoise 在乾淨暗部大平面製造規律 luma/chroma mesh；若原圖暗部平坦而 denoise 後新增高頻網格，受保護 mask 內回退到原圖乾淨像素。
- **0.4.14** — showroom white contrast + gradient smoothing：`showroom_white` 追加等同手動對比 +55 的 luma-only 對比提升；平滑低彩車身面加入極輕微 luma dither，並提高 batch/manual/preview JPEG 品質，降低大面積同色區 posterization / 色階斷層。
- **0.4.15** — showroom white float32 grade chain：`_showroom_white` 改為 float32 全鏈，砍掉鏈內 7 次中途 uint8 量化，1.55× 對比拉伸與所有 tone/HSV/YCrCb 運算都在連續空間執行；`_dither_smooth_neutral_luma` 改用 *拉伸前* 的 luma 算 smooth mask（修掉舊 mask 把拉伸自己產生的階差當 detail 而排除 dither 的盲點），dither 強度 0.75 → 2.5（±1.25 LSB），破掉 denoise 移除自然顆粒後暴露的 8-bit 量化色階。1.55 對比強度與所有 v0.4.11–v0.4.14 守的暗部 chroma grid / mesh / 中性偏冷 / 紫紅減飽和 / luma-only clarity invariant 保留不動。

---

## v0.3 / v0.4 / v0.5（原計畫的 NAFNet / YOLO crop / Hough level）— merged into v0.2.0 ✅

原 ROADMAP 把 NAFNet 降噪（v0.3）、自動裁剪（v0.4）、水平校正（v0.5）拆三個 release。實際走完 v0.1 後重評估，分四次發佈對使用者沒意義（半成品 demo），全部合併到 v0.2.0。新 v0.3.0 變成 adjustment panel，新 v0.4.0 變成 AI Batch Versioning & Quality（上方兩個段落）。

`ARCHITECTURE.md` § Pipeline 順序與 `docs/adr/0002-bundled-v0.2.0-processing.md` 記錄理由。

---

## v0.5.0 — Preset UX Redesign ✅ (shipped)

**目標**：把 Preview 頁的 preset / 處理動作從「混亂的概念湯」收斂成「Lightroom 標準 + 詞彙分家 + 狀態看得見」，解決使用者最早回報的「我移除 preset 但照片還有對比」這條路徑，讓清空照片微調變成單一明確動作。

範圍（已 ship）：
- **Lightroom 標準 preset 語意**：preset = template，載入 = 複製數值，刪除 preset 只移除 template，**不影響任何照片**。徹底放棄 `applied_preset_id` FK / cascade delete 的過度設計。
- **詞彙分家**：AI 那家全部「開始 AI 處理」「AI vN」「AI 色調風格」；手動那家「套用微調」「手動 vN」「Preset」。8 個按鈕全部改名。
- **狀態看得見**：Before/After header 顯示完整 source chain（`原圖 · 手動 v2 — 基於 AI v1 / 展間白`）+ top-3 slider 偏離摘要；PhotoCard 下緣 AI / 手動 雙 chip + 版本數量。
- **動作後果可預期**：每個 state-changing 按鈕旁有 hint 文「會新增 / 不會覆蓋」。
- **「清空照片微調」明確存在**：兩顆按鈕（清空目前 / 清空已選 N 張），新 endpoint `POST /projects/{id}/adjustments/clear` hard-delete `photo_adjustments` + `photo_adjustment_versions` + 磁碟檔 + 清掉 `processed_paths["adjusted"]` cache，視覺切回 AI 版本或原圖。「清空已選 N 張」走 `window.confirm` 二次確認。
- **Preset 管理 modal**：取代既有「刪除 preset...」下拉，附明確 disclaimer。
- **DB schema 不動**：考慮過加 `archived_at` 給 `photo_adjustment_versions`，最後採 hard delete 與 Lightroom 標準語意對齊。

非範圍：
- ❌ `applied_preset_id` 追蹤 / cascade delete
- ❌ AI 版本與手動版本融合
- ❌ 跨照片 preset 同步
- ❌ 永久刪除已 archived AI 版本

對應提案：`openspec/changes/preset-ux-redesign/`（含 proposal / design / 3 個 capability specs / tasks）

子版本：
- **0.5.1** — showroom white highlight/shadow-safe contrast：保留 v0.4.14 起的 luma-only 對比方向，但把最後對比拉伸改成 midtone-weighted + soft-knee luma mapping，避免展示間白牆、白地、白車身亮部被推成大片純白，也避免黑內裝、輪拱、背景被壓成死黑。
- **0.5.2** — draft preview visibility + extra highlight guard：舊的手動 draft 仍會載入 sliders，但不再自動蓋過剛選中的 AI 版本；只有使用者本輪真的動過 slider / 載入 preset / 旋轉 / 幾何後，右側才切成「目前微調預覽」。同時 `showroom_white` 再下修極亮區 lift，降低偶發爆白。
- **0.5.3** — showroom white near-white panel protection：針對暗場景中的大面積低彩度近白區，依原圖 luma/chroma/local-detail 加上 highlight cap，避免白車身、白地板或白牆被對比拉伸成視覺爆白；純白錨點仍保留。

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

### ADR 索引

重大架構決策都留 ADR 在 `docs/adr/`：

- `0002-bundled-v0.2.0-processing.md` — v0.2 / v0.3 / v0.4 / v0.5 合併成單一 release 的理由
- `0003-batch-versioning.md` — v0.4.0 `AI vN` immutable batch path + archive 語意 + 為什麼 version 是 project-scoped
- `0004-gpu-worker-split.md` — v0.4.9 AI worker 拆 CUDA image、沒 GPU 直接 fail 不降級的量化理由

新增重大架構變更請補 ADR，採用同一份格式：Date / Status / Context / Decision / Consequences / Alternatives / References。

### 版本號碼說明

App version 是單一 canonical 值，必須在以下四處同步 bump：

1. `api/main.py` `APP_VERSION` — `/health` 與 FastAPI title 用
2. `web/src/version.ts` `APP_VERSION` — 前端顯示用
3. `web/package.json` `version` — npm 套件 metadata
4. `.github/workflows/deploy-dev.yml` `EXPECTED_APP_VERSION` — CD 部署後的 health gate

`pyproject.toml` 的 `version` 是 Python 套件 metadata，目前慣例與上面四處同步。歷史上 v0.4.x 系列曾漏 bump pyproject，已於 v0.4.9 之後對齊；之後每次發版請四處 + pyproject 一起改。
