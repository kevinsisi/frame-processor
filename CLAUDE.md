# Project Rules — frame-processor

照片批次後製工具。使用者：晴晴。用途：carsmeet.tw 與 8891 車輛照片批次後製。

核心流程：上傳 N 張 → 選風格 → 全部一鍵處理 → 下載 zip。

## Stack

- Backend: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16 + Redis 7 + RQ
- Frontend: React 18 + Vite 5 + TypeScript 5 + TailwindCSS 3
- Worker: RQ worker (Python) — 處理 zip 匯出與後續 AI 後製 job
- Deployment: Docker Compose（api / web / worker / postgres / redis）

## Layout

```
api/         FastAPI app（routers + schemas + database session）
models/      SQLAlchemy ORM + Pydantic 共用 enums
services/    照片處理核心（OpenCV / Pillow / NAFNet / 自動裁剪 / 水平校正 / 色調預設）
worker/      RQ worker entry + jobs
web/         React + Vite + Tailwind 前端
alembic/     DB migrations
deploy/      Dockerfiles + docker-compose
openspec/    Spec-driven change proposals
docs/        Architecture、ADR、設計筆記
```

從 repo 根目錄執行：`uvicorn api.main:app`、`python -m worker.main`、`cd web && npm run dev`。

## Deployment

正式環境：`https://frame.sisihome.org`

- 桌機（Tailscale `100.83.112.20`）跑 Docker Compose stack：`docker compose -f deploy/docker-compose.yml up -d`
- 持久資料已從 Docker Desktop named volumes 遷到 `G:\frame-processor\` bind mounts：`postgres-data`、`storage-data`、`redis-data`。不要改回 named volumes；C 槽空間不足。舊 C 上的 frame-processor named volumes 與舊 Redis anonymous volume 已於 2026-05-08 遷移後移除。若重建或換機，必須先建立這三個目錄並把既有資料複製進去再啟動；空目錄會啟動成空 DB/storage。
- CI/CD：`.github/workflows/docker-publish.yml` push `main` 時 build/push `kevin950805/frame-processor-api:<commit-sha>` 與 `kevin950805/frame-processor-web:<commit-sha>`，並更新 `latest` alias；`.github/workflows/deploy-dev.yml` 在 publish 成功後透過桌機 Windows OpenSSH Server 到 `100.83.112.20`，複製 `deploy/docker-compose.yml` 到 `D:/GitClone/_HomeProject/frame-processor/deploy/docker-compose.yml`，寫 `deploy/.env`，再上傳並執行 PowerShell scripts。Deploy 用 GitHub `DOCKERHUB_TOKEN` 建立臨時 Docker auth config、scp 到桌機、逐一 `docker pull` postgres/redis/api/web images，接著用該 commit SHA tag 執行 `docker compose up -d --pull never --no-build`，避免 Windows Docker credential helper 需要互動 logon session；臨時 auth config 不可 commit，workflow/script 必須清掉 local 與 remote 檔案。CD 必須在 up 前驗證三個 G 槽資料目錄存在且 compose 解析為 G 槽 bind mounts，並驗證 `SETTINGS_ADMIN_TOKEN` 仍存在；up 後用 `docker inspect` 確認 runtime images 使用該 commit tag 且 mounts 仍是 G 槽 bind，不可回到 Docker Desktop C 槽 named volumes。`GEMINI_API_KEY` 只是 DB key pool 之外的 runtime fallback，不可當成 deploy blocker。
- CI/CD secrets：`DOCKERHUB_TOKEN`、`DEPLOY_SSH_KEY`、`DEPLOY_USER`、`TS_OAUTH_CLIENT_ID`、`TS_OAUTH_SECRET`；`DOCKERHUB_USERNAME` 預設 `kevin950805`。`GEMINI_API_KEY`、`SETTINGS_ADMIN_TOKEN`、`KEY_MANAGER_URL` 若在 GitHub secrets 有提供才更新到桌機 `deploy/.env`，否則保留桌機既有值；CD merge 後必須驗證 `SETTINGS_ADMIN_TOKEN` 仍存在。`GEMINI_API_KEY` optional fallback，不可因缺少它而阻擋 deploy。`KEY_MANAGER_URL` optional。CD 固定 `GEMINI_MODEL=gemini-2.5-flash`。`SETTINGS_ADMIN_TOKEN` 只進 api/worker runtime env，不可 bake 進 static web image。
- 唯一對外 port 是 web container 的 `100.83.112.20:8533`（nginx）— api/postgres/redis 不外露；api debug 用 `127.0.0.1:8633`
- web container 的 nginx 把 `/api/*` reverse proxy 到 `api:8000/*`（剝掉 `/api`），所以前端走同源
- 前端 build 時 `VITE_API_BASE_URL=/api`（在 `deploy/docker-compose.yml`）
- API 的 `ALLOWED_ORIGINS` 必須包含 `https://frame.sisihome.org`
- RPi (`rpi-matrix`) Caddy 反向代理：`frame.sisihome.org` → `100.83.112.20:8533`，`request_body.max_size 500MB`，設定在 `/home/kevin/DockerCompose/caddy/Caddyfile` 的 `*.sisihome.org` block 裡
- Caddy 改設定後一律 `docker restart caddy`（不是 reload）

### v0.2.0 處理 pipeline 必要條件

- `GEMINI_API_KEY` env 是水平校正的 optional fallback；v0.2.2 起也可在 `/settings` 批次匯入 Gemini keys，DB key pool 會優先於 env，無任何 key 則 level_correct step 會 fail。Deploy 不強制要求 host `.env` 有 fallback key，避免把可在 DB 管理的金鑰寫死成發布前置條件。`/settings` 的 PUT/DELETE/sync mutation 需要 `SETTINGS_ADMIN_TOKEN`。key-manager 不是本系統依賴；只有明確設定後端 `KEY_MANAGER_URL` 時才啟用可選同步入口，不接受前端任意 URL。
- 模型權重 lazy download 寫到 `G:\frame-processor\storage-data\models-weights\{ultralytics,nafnet}`；首次處理會下載 ~70MB（NAFNet）+ 6MB（YOLO），之後跨 container restart cached
- worker image build 會拉 CPU-only torch wheel（避免 CUDA 多 GB），有 GPU 也只在 `torch.cuda.is_available()` 為 true 時自動用
- pipeline 順序固定 `denoise → lens_distort → level → crop → grade`，理由見 `ARCHITECTURE.md` § Pipeline 順序

### v0.3.0 手動調整面板現況

- `/preview` 支援點選照片同步上方 Before/After；不要再固定第一張 processed sample。
- 手動調整目前走同步 preview/apply API：`POST /photos/{id}/preview` 回小張 JPEG，`POST /photos/{id}/adjustments` 寫出 `processed_paths.adjusted`。
- Preview API 必須先把來源縮成小圖再套用手動旋轉/色調/幾何，避免手機原圖每次 preview 卡數十秒；full-resolution render 只屬於按「產生」後的版本輸出。
- 可對每張照片獨立點按向左/向右 90 度旋轉，並可調整手動水平、裁切縮放/偏移、手動變形修正、曝光、對比、亮部、暗部、色溫、色偏、飽和、自然飽和、清晰度、銳利化與 HSL 六色區。
- 90 度 orientation 旋轉與所有 slider 調整先存在該照片的 `photo_adjustments.params` 草稿，點按/拖曳後需立即更新 Before/After 原圖側與 live preview 側，且重開網頁要載回草稿。
- 只有使用者按「產生目前版本」或「產生已選版本」時才建立 `photo_adjustment_versions` 與 `manual-vN.jpg`；單純操作 slider/旋轉不得建立版本。
- 幾何類操作（水平、裁切、裁切 X/Y、變形修正）需集中在全螢幕單圖構圖工作區，讓使用者看到格線覆蓋並拖曳裁切框，且要有取消/完成語意；不要只散落在一般色彩 slider，也不要用擁擠的雙欄小 modal。
- 未明確選版本時，Manual adjustment 從非 `adjusted` 的基準圖重新計算，不得把內部 latest adjusted 當來源累加；若使用者在照片卡片版本下拉明確選擇原圖、批次版本或手動 vN，該版本就是後續 preview/apply/download 的來源。
- 手動水平、裁切、變形修正路徑不得呼叫 Gemini AI；AI level correction 只屬於原本 batch pipeline。
- 使用者 preset 存在 `adjustment_presets`；單張調整參數存在 `photo_adjustments`。
- 手動產生版本存在 `photo_adjustment_versions`；照片卡片版本下拉必須可選原圖、pipeline preset、各手動版本，並同步切換卡片圖、上方 Before/After 基準、手動調整來源與下載目標。未手動指定版本時，live preview 預設從原圖套用目前 pipeline 色調選擇；批次處理完成後才自動切到剛產生的 preset 版本。UI 不可暴露 `adjusted`、`latest`、raw preset key 等內部狀態名稱。
- PipelinePanel 預設值：AI 降噪重度、廣角畸變矯正開啟、Gemini Vision 水平校正開啟、自動裁剪原圖比例；主要「開始產生」動作放在手動微調區塊下方。色調 preset 必須有可見差異，OpenCV fallback 降噪不得弱到使用者在重度模式看不出效果。
- 匯出 zip 順序必須是 `adjusted` → 任一 pipeline processed preset → original。
- 「套用到已選照片」走 `adjustment_jobs` worker job 與輪詢進度。

### v0.x destructive schema reset playbook

v0.x 期間若 alembic revision id 對不上（例：branch supersede 舊版 0002 後新版 0002 名字不同，DB 版本指向已被刪除的 revision），按以下步驟處理：

1. 進 postgres：`docker exec frame-processor-postgres-1 psql -U frame -d frame_processor`
2. 用 `\d <table>` 確認哪些 v0.2 物件已存在
3. `DROP TABLE IF EXISTS processing_jobs CASCADE;` + `ALTER TABLE photos DROP COLUMN IF EXISTS processed_paths;` + `DROP TYPE IF EXISTS color_grade_preset, processing_job_status, aspect_ratio, denoise_strength CASCADE;`
4. `UPDATE alembic_version SET version_num = '0001_initial';`
5. `docker compose -f deploy/docker-compose.yml restart api` — entrypoint 的 `alembic upgrade head` 會自動把新 0002 跑起來

**Project / Photo 表保留**（projects / photos / exports 屬於 0001 schema，不動）。NEVER 在 v1.0 之後做這個 — 那時要正規 migration 升級。

## Global Working Rules

- Read the current code, files, and runtime context before deciding on a change.
- Prefer the smallest correct fix over broad refactors.
- Fix root causes, not only visible symptoms or display-layer effects.
- When the best next step is already clear, execute it instead of asking redundant confirmation.
- Do not send the user through intermediate debugging steps you can perform directly.
- Do not use regex to parse structured formats when explicit parsing or a proper parser is more reliable.
- For new projects, major features, rewrites, or redesigns with unresolved decisions, present a reviewable plan before writing product code.
- Parallelize independent work when it meaningfully reduces turnaround; keep the main thread focused on coordination and synthesis.
- Frame each task clearly with the actual problem, constraints, and expected end state.
- Do not replace user intent with hardcoded fallback values after a failure.
- Retry transient external or AI failures with backoff; when retries are exhausted, surface the real failure.
- Add per-item timeouts to batched external calls so one slow request does not block the whole batch.
- Keep user keywords and search intent unchanged unless the user explicitly asked for transformation.
- Verify behavior in a real runnable environment whenever feasible.
- Do not claim CI, CD, deployment, or runtime success from guesswork; use trustworthy evidence.
- When a code change is complete, treat follow-through as part of the work, not an optional extra.
- Every code change must update memory, update spec, commit, and push unless the user explicitly says not to.
- Prefer commit-first, push-later batching for larger work groups when repeated pushes would only retrigger CI/CD without adding review value.
- If a requirement should govern future implementation, write it into the formal rule sources instead of leaving it only in chat context.
- Avoid magic numbers in implementation; prefer existing enums, or introduce named constants when no enum exists.
- For nullable numeric columns whose valid range includes `0` / `0.0` / `False`, never use the `value or default` idiom — `0` is falsy in Python and the idiom silently rewrites valid input. Always use `value if value is not None else default`.
- Before commit, confirm AI-generated methods, classes, and files are actually used; remove unused junk instead of committing it.
- Build checks before commit must use the repo's concrete command(s), not vague "validation" language.
- For any non-trivial feature request or requirement, first confirm requirements with the user and define OpenSpec before implementation.
- For major changes, use a brainstorming step before proposal or implementation.

## Domain-Specific Rules

- **照片是大檔（5–25MB）**：不要在 API 回應裡 base64 inline 整張原圖；用 `/photos/{id}/file` endpoint 串流。預覽圖（thumbnail）可以 inline。
- **原圖永不覆寫**：處理結果寫到不同路徑（`<storage>/projects/<id>/processed/<photo_id>.<preset>.jpg`），原圖永遠在 `<storage>/projects/<id>/originals/<photo_id>.<ext>`。
- **EXIF orientation**：iPhone / DJI 直拍照片帶 `Orientation=6/8`，讀取時必須套用旋轉，否則 thumbnail 會躺著。所有 `services/storage.py` 的 PIL 讀取都應該 `ImageOps.exif_transpose()`。
- **色調預設名稱用 enum**：禁止字串散落在 routers / services / FE，全部走 `models/enums.py:ColorGradePreset`。
- **batch 處理永遠走 worker**：FastAPI handler 不做 CPU 重的事；上傳 / 列表 / 觸發 job / 查狀態 / 下載 zip 是 API 的責任。處理本身一律 enqueue 到 RQ。

## Skill Activation Rules

Treat the following skill files as active workflow rules for this workspace, even if the host AI environment does not expose them through a built-in skill registry. Apply them automatically by task type:

- Treat `skills/execution-style/SKILL.md` as the default execution behavior for normal implementation work
- Treat `skills/plan-before-build/SKILL.md` as mandatory for new projects, major features, and large redesigns before implementation begins
- Treat `skills/project-stack-standard/SKILL.md` as mandatory when choosing or reviewing app/service stack, backend setup, database choice, or monorepo structure
- Treat `skills/root-cause-debugging/SKILL.md` as mandatory for bug investigation and regressions
- Treat `skills/integration-robustness/SKILL.md` as mandatory for AI calls, external APIs, retries, and batched integrations
- Treat `skills/verification-and-evidence/SKILL.md` as mandatory when reporting runtime, CI, CD, or deployment status
- Treat `skills/completion-checklist/SKILL.md` as mandatory for any code change before reporting completion
- Treat `skills/deployment/SKILL.md` as mandatory for deployment, Docker, reverse-proxy, CI/CD, and release work
- Treat `skills/frontend-design/SKILL.md` as mandatory for frontend creation or redesign work
- Treat `skills/skill-creator/SKILL.md` as the active workflow when creating, improving, or evaluating a skill
- Treat `.github/skills/openspec-explore/SKILL.md` as the active workflow when the user wants exploration without implementation
- Treat `.github/skills/openspec-propose/SKILL.md` as the active workflow when creating a new OpenSpec change
- Treat `.github/skills/openspec-apply-change/SKILL.md` as the active workflow when implementing an OpenSpec change
- Treat `.github/skills/openspec-archive-change/SKILL.md` as the active workflow when archiving a completed OpenSpec change

Mirror locations (`.claude/skills/`, `.gemini/skills/`, `.opencode/skills/`, `.github/skills/`) hold the same OpenSpec workflow skills so Claude Code, Gemini CLI, opencode, and GitHub Copilot all see them. The canonical source for general workflow skills lives in `skills/`.

`skills/agent-design/` and `skills/key-pool-standard/` 已從 template 移除（本專案 v0.x 不會有 AI agent / multi-key pool；若未來引入再加回）。

## Persistent Standards

- Every code change must update memory (if applicable), update OpenSpec (if applicable), commit, and push.
- Complex tasks must carry workflow checkpoints in the task list.
- 對於非 trivial 的 feature request，先 brainstorming → OpenSpec 提案 → 實作。

## Project Architecture Pointers

- `ROADMAP.md` — phase 路線圖（v0.1 walking skeleton 已完成；v0.2+ 為 AI 處理 phase）。新對話先讀這個對齊大方向。
- `ARCHITECTURE.md` — 系統架構、資料流、容器拓樸、儲存路徑慣例。
- `openspec/changes/` — 進行中的提案；archived 在 `openspec/changes/archive/` 下。
- 程式碼本身：
  - `api/main.py` — FastAPI app + CORS + router 掛載
  - `api/routers/projects.py`、`api/routers/photos.py`、`api/routers/exports.py`
  - `models/database.py`、`models/project.py`、`models/photo.py`、`models/export.py`、`models/enums.py`
  - `services/storage.py`（檔案存取）、`services/zip_export.py`（zip 打包）、`services/photo_processor.py` 等 stub
  - `worker/main.py`（RQ entry）、`worker/jobs.py`（zip 與後續 AI job）
