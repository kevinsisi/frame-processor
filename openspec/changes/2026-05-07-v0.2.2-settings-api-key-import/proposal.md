# v0.2.2 — Settings Page + API Key Import

**Status**: approved for implementation
**Date**: 2026-05-07
**Author**: Kevin

## Why

v0.2.1 的水平校正需要 `GEMINI_API_KEY`，但目前只能靠 deploy host `.env` 設定。實際營運需要不用重啟服務也能批次匯入 / 清空 / 從 key-manager 同步 Gemini keys，並在 UI 看到目前來源與遮罩後四碼。

`media-processor` 已有可用的設定頁模式；本次沿用它的 UX 與資料流，但改成 frame-processor 的同步 FastAPI + SQLAlchemy 結構。

## What Changes

### Backend

- 新增 `app_settings` table，存 runtime-managed `gemini_api_keys`。
- 新增 `services/settings_store.py`：解析 textarea paste、DB 優先 / env fallback、遮罩摘要、清空 DB key pool。
- 新增 `api/routers/settings.py`：
  - `GET /settings`：回傳 Gemini model + key pool 摘要。
  - `PUT /settings/gemini-api-keys`：批次匯入，支援取代或合併。
  - `DELETE /settings/gemini-api-keys`：清空 DB pool，回到 env fallback。
  - `POST /settings/sync-from-key-manager`：從 key-manager trusted-only export 同步。
- settings mutation 需要 `SETTINGS_ADMIN_TOKEN`，且 key-manager sync URL 固定由後端 `KEY_MANAGER_URL` 提供，避免公開端任意改 key 或 SSRF。
- `services/level_correct.py` 改用 settings store 取得 active key；DB pool 有值時優先用 DB，否則 fallback `GEMINI_API_KEY`。
- NAFNet 權重來源 401 時，降噪改用 OpenCV fallback，不讓整批處理直接失敗。

### Frontend

- 新增 `/settings` route 與 header link。
- 新增 `web/src/pages/Settings.tsx` + CSS，參考 `media-processor` 設定頁：目前狀態、textarea 批次匯入、取代/合併、清空、key-manager 同步。
- `web/src/api/client.ts` / `web/src/types.ts` 新增 settings API types。
- mobile header / pipeline / job-status 溢出與 before-after slider clip 對齊一起修正，避免設定頁 nav 加重既有跑版。

### Version

- bump `pyproject.toml`、`web/package.json`、`web/src/version.ts` 到 `0.2.2`。

## Non-Goals

- 不實作 v0.3.0 微調面板。
- 不新增多 key retry / rotation；本次只讓 runtime key pool 可管理，後續 Gemini Vision 強化再接 key rotation。
- 不把完整 API key 回傳給前端；只回遮罩後四碼。

## Acceptance Criteria

- `GET /settings` 在沒有 DB keys 時顯示 env fallback 或 none。
- `PUT /settings/gemini-api-keys` 可接受換行、逗號、`GEMINI_API_KEY=...`、`export GEMINI_API_KEY=...` 格式並去重。
- `DELETE /settings/gemini-api-keys` 清空 DB keys 後回到 env fallback。
- `POST /settings/sync-from-key-manager` 能解析 key-manager `/api/keys/export?trusted_only=1` 的 grouped keys。
- `/settings` UI 可完成上述操作，且不顯示完整 key。
- 未提供正確 `SETTINGS_ADMIN_TOKEN` 時，PUT/DELETE/sync 會被 403 擋下。
- mobile preview 不產生橫向溢出，before-after slider 的 after 圖不因 clip 寬度被重新縮放。
- `python -c "import api.main, services.settings_store, services.level_correct"` 通過。
- `cd web && npm run build` 通過。
