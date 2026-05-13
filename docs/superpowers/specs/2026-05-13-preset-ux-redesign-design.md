# Preset UX 重設計 — 設計文件

- **日期**: 2026-05-13
- **狀態**: Draft（brainstorming 產出，待使用者 review → 進 OpenSpec proposal → 實作）
- **目標版本**: v0.5.0
- **作者**: Kevin × Claude (Opus 4.7)
- **Brainstorm session**: `.superpowers/brainstorm/2769-1778650676/`

## 1. 背景

現行 Preview 頁的 preset / 處理動作對使用者（晴晴）造成系統性混亂。腦力激盪期間定位了四個根本原因：

1. **資料模型沒先教**：使用者不知道「原圖永不變、每按一次產生 = 新檔案、版本下拉決定當下視覺」這套規則；按按鈕像賭結果。
2. **詞彙混疊**：「preset」「產生」「版本」每個詞至少兩個意思（AI 一套 / 手動一套），名稱不講人話。
3. **狀態不可見**：盯著一張照片，UI 不告訴你它現在是 AI v1 還是手動 v3、套了什麼風格；版本下拉藏在角落、語意含糊。
4. **動作後果不可預期**：按下去之前無法判斷會新增 / 覆蓋 / 影響哪些；「刪除 preset」對使用者直覺是 undo，實際只刪 template，這是使用者最初回報的痛點。

使用者原始抱怨「我已經移除 preset 了，但照片還是有對比」就是 #1 + #4 的疊加結果。

## 2. 設計目標（四個原則）

| 原則 | 意思 |
|---|---|
| 01 狀態永遠看得到 | Before/After 標題列、照片卡片下緣明確顯示「目前 = AI v? + 手動 v? + 用什麼 preset」 |
| 02 詞彙分家 | AI 那家全用「AI 處理 / AI vN / AI 色調風格」；手動那家全用「微調 / 手動 vN / Preset」。兩家詞彙不重疊 |
| 03 動作後果可預期 | 每個動作按鈕旁有一行 hint：會新增什麼 / 不會覆蓋什麼 / 對其他版本影響為何 |
| 04「清空微調」明確存在 | 跟「刪除 preset」徹底分開。Preset 是 template、永遠不影響任何照片；要回到「沒微調」走「清空照片微調」這個獨立動作 |

## 3. 資料模型（不變，但要被 UI 看見）

設計依此事實，**不修改 schema**：

- 原圖：`<storage>/projects/<id>/originals/<photo_id>.<ext>`，永不覆寫
- AI 批次版本：每次按「開始 AI 處理」產生 `<storage>/projects/<id>/batch-v<N>/<photo_id>.jpg`，N 單調遞增、舊版不刪
- 手動微調版本：每次按「套用微調」產生 `manual-v<N>.jpg`（依現有 `photo_adjustment_versions` 慣例），舊版不刪
- 「目前這張」= 照片卡片版本下拉指向的版本，其他版本仍在磁碟
- Preset 兩種：
  - `ColorGradePreset` enum（展間白 / 戶外暖 / 夜間冷）— AI 批次處理的色調 preset
  - `AdjustmentPreset` ORM row — 使用者儲存的 sliders template；載入 = 複製數值；刪除 = 只刪 template，**不影響任何照片或版本**

設計刻意不引入 `applied_preset_id` FK 或 cascade delete — 之前曾考慮，後確認違反 Lightroom 標準 preset 語意，且使用者明確表態 preset = 純 template / 快速設定。

## 4. 範圍變更清單

### 4.1 FE 文案（純改名）

| 舊 | 新 | 所屬層 |
|---|---|---|
| 開始產生 | 開始 AI 處理 | AI |
| 產生目前版本 | 套用微調到目前照片 | 手動 |
| 產生已選版本 | 套用微調到已選照片 | 手動 |
| 重設 | 清空目前照片的微調 | 手動 |
| （無對應） | 清空已選照片的微調 | 手動（新動作）|
| 色調風格（Upload 頁）| AI 色調風格 | AI |
| 載入 preset... | 選 preset 載入數值 | 手動 template |
| 刪除 preset... | 收進「⚙ 管理」modal | 手動 template |

### 4.2 FE 狀態列（新組件 / 修改 BeforeAfter）

**Before/After header**

```
[Before: 原圖] · [After: 手動 v2 ─ 基於 AI v1 / 展間白 · 對比 +25 / 色溫 +120]
```

- 「After」段落顯示完整 source chain（AI 那層 + 手動那層 + 主要 sliders 偏離值）
- 主要偏離值定義：絕對值 ≥ 預設的兩倍視為「主要」，最多顯示 3 個

**照片卡片下緣**

```
[thumbnail]
[AI v1] [手動 v2]  ▼ 4 個版本
```

- 兩個 chip：當前 AI vN（或「無 AI」）+ 當前手動 vN（或「無手動」）
- 旁邊「▼ N 個版本」按下打開既有的版本下拉
- 兩個 chip 用不同邊色：AI = `#7aa8d8`，手動 = `#d8a87a`（對應 mockup）

### 4.3 FE Preset 管理 modal（新組件）

打開：手動微調面板「⚙ 管理」按鈕

```
管理 Presets                             [✕]
─────────────────────────────────────
[ 晴晴常用調   ]  [重新命名] [刪除]
[ 高對比戶外   ]  [重新命名] [刪除]
─────────────────────────────────────
ℹ 刪除 preset 只移除 template，不會動到任何照片。
   要清空照片上的微調請用主面板的「清空」按鈕。
```

- 沿用既有 `DELETE /adjustment-presets/{id}` endpoint
- 「重新命名」是 nice-to-have，第一版可只實作刪除 + 名字 inline edit

### 4.4 FE 新動作：「清空照片微調」

兩顆按鈕（手動微調面板「清空」區）：

- **清空目前照片的微調** — 對 active photo
- **清空已選 N 張的微調** — 對 selected

行為：
1. Reset 該照片的 `photo_adjustments` 草稿到 DEFAULT
2. Archive 該照片所有 `photo_adjustment_versions`（沿用既有 archive 機制；檔案不刪，但下拉列不指它）
3. 把版本下拉自動切回該照片最新的 AI vN；若無 AI vN 則切回原圖
4. 觸發 Before/After 重繪

### 4.5 BE 新 endpoint

```
POST /projects/{project_id}/adjustments/clear
Body: { "photo_ids": [UUID, ...] }
Response: { "cleared_count": int, "photos": [PhotoOut, ...] }
```

實作要點：
- 每張照片：刪 `photo_adjustments` row（或 reset 成預設）
- 對 `photo_adjustment_versions` 表的對應 row 設 `archived_at`（沿用 v0.4.x archive 慣例）
- 不真的刪磁碟檔案（保留可回滾）
- Recompute 各照片的 active version selector（依 v0.4.x 規則：archived 跳過、選最新非 archived 的 AI 或原圖）

### 4.6 Upload 頁

唯一改動：`StylePicker` 標題「色調風格」→「AI 色調風格」+ 一行說明文（已存在的 upload-form__hint 改寫即可）：

```
這是 AI 批次處理用的色調 preset，不是手動微調 preset。
進 Preview 後自動跑的 AI 批次會用這個風格。
```

## 5. 非範圍（YAGNI）

- ❌ `photo_adjustments.applied_preset_id` FK / cascade delete — 違反 Lightroom 標準語意，使用者明確不要
- ❌ AI 版本與手動版本融合 / 自動 chain renderer — 兩條鏈仍獨立
- ❌ 跨照片 preset 同步（preset 內容變了，回頭更新所有套過的照片）
- ❌ DB schema 改動 — 完全不動 alembic
- ❌ 自訂 preset bundle（v0.6 / v0.7 phase 才做）
- ❌ 手動微調支援多 preset 比較 / 預覽 — 單一 preset 工作流

## 6. 測試

- **Backend**：`tests/test_adjustments_clear.py` 新檔，testcontainers Postgres + TestClient + fake RQ（依賴 `add-frame-test-harness`，若未完成則先用 pure-function 測試 archive 邏輯）
  - 清空後 `photo_adjustments` 為 default
  - 清空後 `photo_adjustment_versions` 的 `archived_at` 已寫入
  - Recompute 後 active version 為最新 AI vN 或原圖
  - Project 內混合「有套微調 / 沒套微調」的照片，只清前者
- **FE**：
  - PhotoCard 狀態 chip 在不同 photo state 下渲染正確
  - BeforeAfter header 顯示完整 source chain 字串
  - 「清空」按鈕呼叫 clear endpoint、樂觀更新本地 state
  - Preset modal 開關、刪除、cancel 行為
  - 各個改名按鈕的 onClick handler 正確（regression）

## 7. 實作分工建議

按 dependency 排序：

1. **BE：clear endpoint** — `api/routers/adjustments.py` 加 `POST /clear`、服務層加 `clear_adjustments_for_photos(photo_ids)`
2. **FE 文案改名** — 8 個按鈕、Upload 頁說明、AdjustmentPanel hint 文，沒功能風險
3. **FE 狀態 chip 組件** — PhotoCard 改造，純 read 現有 photo state
4. **FE BeforeAfter header status** — 讀現有 photo state，新元件
5. **FE 清空按鈕串接** — 呼叫 step 1 的新 endpoint
6. **FE Preset 管理 modal** — 新組件，沿用既有 deleteAdjustmentPreset
7. **FE Upload 頁改名 + 說明文** — 最簡單，放最後

## 8. 風險 / 開放問題

- **手機版 layout**：BeforeAfter header 的完整 source chain 字串可能太長。Fallback：mobile 顯示 `AI v1 + 手動 v2` 不展開 sliders 摘要，desktop 才展開。
- **多 preset 偏離值顯示閾值**：「主要偏離 sliders」的定義是「絕對值 ≥ 預設兩倍」，這個閾值要實機跑過確認感覺對。
- **「清空已選」對混合狀態的處理**：若已選 12 張內有 3 張本來就沒微調、9 張有，新 endpoint 應該對這 3 張 no-op（不算 error），response `cleared_count` 為 9。
- **Archive 不是 delete**：使用者期待 `manual-v?.jpg` 被「移除」，但實際只 archive。要不要在 modal 提供「永久刪除已 archived 版本」？這版先不做，列入 v0.5.x 後續優化。

## 9. 開發成本估算

| 項目 | 估算 |
|---|---|
| BE endpoint + 服務層 + 單元測試 | 0.5 天 |
| FE 文案全改 + hint 文 | 0.5 天 |
| FE 狀態 chip 組件 | 0.5 天 |
| FE BeforeAfter header | 0.5 天 |
| FE 清空按鈕串接 | 0.5 天 |
| FE Preset modal | 1 天 |
| FE Upload 頁改名 + 說明 | 0.25 天 |
| 整合測試 + smoke | 0.75 天 |
| **合計** | **約 4.5 個人日** |

## 10. 參考

- 腦力激盪歷程：`.superpowers/brainstorm/2769-1778650676/content/`（photo-flow-explained.html / design-direction.html）
- 既有 v0.3.0 OpenSpec：`openspec/changes/2026-05-07-v0.3.0-adjustment-panel/`
- 既有 v0.4.0 batch version control：`openspec/changes/2026-05-10-batch-version-control/`
- 既有 Preview UX 審查：`docs/preview-ux-audit.md`
