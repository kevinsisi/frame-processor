# v0.5.0 - Preset UX Redesign

**Status**: proposed
**Date**: 2026-05-13
**Author**: Kevin × Claude (Opus 4.7)
**Design doc**: `docs/superpowers/specs/2026-05-13-preset-ux-redesign-design.md`

## Why

Preview 頁的 preset / 處理動作對使用者（晴晴）造成系統性混亂，brainstorming 期間定位四個根本原因：(1) 資料模型（原圖永不變、按產生 = 生新檔、版本下拉決定當下視覺）沒先教使用者；(2) 詞彙混疊 — 「preset」「產生」「版本」每個詞至少兩個意思（AI 一套 / 手動一套）；(3) 狀態不可見 — 盯著一張照片不知道它現在是 AI v1 還是手動 v3、套了什麼風格；(4) 動作後果不可預期 — 「刪除 preset」對使用者直覺是 undo，實際只刪 template，這是使用者最初回報的痛點。

## What Changes

- **FE 文案改名**：8 個按鈕全部講人話（「開始產生」→「開始 AI 處理」、「產生已選版本」→「套用微調到已選照片」、「重設」→「清空目前照片的微調」、「色調風格」（Upload）→「AI 色調風格」、「載入/刪除 preset」→「⚙ 管理」modal 等），AI 詞彙與手動詞彙不重疊。
- **FE 狀態組件**：Before/After header 顯示完整 source chain（「After: 手動 v2 — 基於 AI v1 / 展間白 · 對比 +25 / 色溫 +120」）；PhotoCard 下緣兩個 chip（AI vN + 手動 vN）+「N 個版本」入口。
- **FE Preset 管理 modal**：取代現有「刪除 preset...」下拉，附明確說明「刪除 preset 只移除 template，不會動到任何照片」。
- **FE 新「清空照片微調」動作**：兩顆按鈕（清空目前 / 清空已選），跟「刪除 preset」徹底分開；reset sliders + archive `photo_adjustment_versions` + 切回 AI vN 或原圖。
- **BE 新 endpoint**：`POST /projects/{id}/adjustments/clear`，接 `photo_ids[]`，原子化執行 reset + archive + recompute active version。
- **DB schema 完全不動** — 刻意不引入 `applied_preset_id` FK 或 cascade delete，違反 Lightroom 標準 preset 語意，且使用者明確不要。

## Capabilities

### New Capabilities
- `manual-adjustment-workflow`: 手動微調的完整工作流 — 套用 sliders、清空照片微調、preset template 管理（load / save / delete-template-only），以及這些動作的可預期性（hint 文、確認框、語意）。
- `photo-version-display`: Preview 頁的「目前這張照片是什麼」視覺呈現 — PhotoCard 狀態 chip、Before/After header 的 source chain 標題、版本切換入口。
- `ai-batch-vocabulary`: AI 批次處理區的詞彙與按鈕標籤 — 「開始 AI 處理」「AI 色調風格」「AI vN」等與手動詞彙明確分流。

### Modified Capabilities

無（首次引入這三個 capability；此前的變更走舊 schema，沒有對應 capability spec）。

## Impact

**Affected code**:
- `web/src/components/AdjustmentPanel.tsx` + `.css` — 重構成新動作分組
- `web/src/components/PipelinePanel.tsx` — 改名「開始 AI 處理」
- `web/src/components/PhotoGrid.tsx` + 新組件 `PhotoVersionChip.tsx`
- `web/src/components/BeforeAfter.tsx` — header 改寫 source chain
- `web/src/pages/Upload.tsx` — `StylePicker` 標題加「AI 」字 + hint 文重寫
- 新組件 `web/src/components/PresetManagerModal.tsx`
- `web/src/pages/Preview.tsx` — 串新 endpoint
- `web/src/api/client.ts` — 新 `clearPhotoAdjustments`
- `api/routers/adjustments.py` — 新 `POST /clear` route + schema
- `services/adjustment_renderer.py` 或 `services/adjustments.py` — clear 服務層
- `tests/test_adjustments_preview.py` 或新檔 — clear endpoint 覆蓋率

**Not affected**:
- `alembic/` — DB schema 不動
- `services/photo_processor.py` / AI pipeline — 處理鏈不動
- `models/` — ORM 不動
- 既有 archive 機制（v0.4.x）— 沿用，不改

**Dependencies**:
- 整合測試需要 `add-frame-test-harness`（backlog change，目前 deferred）。第一版優先 pure-function 單元測試覆蓋 service 層，TestClient 整合測試延後到 test-harness 完成。
