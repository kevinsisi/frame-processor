# v0.3.0 — Manual Adjustment Panel (Lightroom-style)

**Status**: proposed (awaiting sign-off — no code yet)
**Date**: 2026-05-07
**Author**: Kevin

## Why

v0.2.0 ship 後晴晴實際使用發現：preset + auto-pipeline 出來的結果 80% 場景 OK，但對特定光線（夕陽逆光、室內燈混色、夜拍車燈反光）需要手動微調才能上稿。每張車照重新跑一次 batch 太慢，需要 in-context 微調 → 即時預覽 → 滿意後再寫入 processed。

直接在 v0.2.0 內加 sliders 會把 v0.2.0 commit 變成「ship 不出去」的長線重構：sliders 是 14+ 參數 + HSL + live preview rendering pipeline，本身就需要架構決定（client-side WebGL vs server-side debounced render vs hybrid）。拆成獨立 v0.3.0 release。

## What Changes

### Backend (services + API)

新增 `services/adjustments.py`：純 Pillow + numpy + OpenCV 實作以下 ops，套用順序固定：

1. `white_balance_offset(image, temp, tint)` — 色溫（藍↔黃）+ 色調（綠↔洋紅）偏移
2. `exposure(image, ev)` — ±5 EV 線性增益
3. `contrast(image, amount)` — S-curve 對比
4. `highlights_shadows(image, hl, sh, whites, blacks)` — 4 通道 tone curve（Lightroom 風格）
5. `hsl(image, ranges)` — 紅/橙/黃/綠/藍/紫 6 個色相區間，每區間 H/S/L 各一個 slider（共 18 個 value）
6. `saturation(image, amount)` — 全域飽和
7. `vibrance(image, amount)` — 智慧飽和（保護膚色 / 已飽和區）
8. `clarity(image, amount)` — 中頻對比（unsharp mask on luminance）
9. `sharpness(image, amount, radius, threshold)` — Lightroom 風格銳化

範圍：每個 slider `-100 ~ +100`（除了 EV 是 `-5 ~ +5`）。0 = no-op。

新增 `models/photo_adjustment.py:PhotoAdjustment` 表（一張 Photo 對應 0 或 1 組調整參數，JSON column 存 14+ 參數）。

新增 `models/adjustment_preset.py:AdjustmentPreset` 表（自訂 preset：name + JSON params + created_at + project_id 可空 = 全域 preset）。

新增 API：
- `POST /photos/{id}/adjustments` body 全套 14+ 參數 → 觸發 worker render → 寫到 `processed/{photo_id}.adjusted.jpg`，回傳 ProcessingJob
- `POST /photos/{id}/preview` body 同上 → **同步**回傳 small JPEG (long-edge 800px) 給 live slider
- `POST /projects/{id}/apply-adjustments` body adjustment_id → 套用到全 project 所有 photo
- `POST /adjustment-presets` 儲存 / `GET /adjustment-presets` 列出 / `DELETE /adjustment-presets/{id}`

### Frontend

- `web/src/components/AdjustmentPanel.tsx` — 14+ slider grid（按 Lightroom 分組：Light / Color / HSL / Detail）
- `web/src/components/HslWheel.tsx` — 6 色相區間 H/S/L 三軌 slider
- `web/src/components/PresetManager.tsx` — 儲存 / 載入 / 刪除自訂 preset
- live preview：slider drag → debounced 300ms → POST /preview → 換掉 BeforeAfter 的 after image
- "套用到全部" 按鈕 → POST /apply-adjustments → 進度條（用 v0.2.0 的 ProcessingJob 流）
- 單張選取 mode：在 PhotoGrid 上 click 一張 → 進入 AdjustmentPanel mode；其他照片 disable

### DB migration `0003_adjustment_panel.py`

新增 `photo_adjustments` + `adjustment_presets` 表；`Photo.processed_paths` 加 `"adjusted"` key 存最終手動調整輸出路徑。

## Non-Goals (defer)

- ❌ 局部調整（gradient mask / radial / brush）— Lightroom 高級功能，v0.4+
- ❌ 鏡頭校正自訂（v0.2 已有 lens distort，但係數不開放 UI）
- ❌ 噪點 NR + 細節保護的 advanced denoise（v0.2 NAFNet 強度 3 段已夠用）
- ❌ Camera profile（DCP）支援
- ❌ 批次微調 per-photo override（套全部 = 共用一組參數，不能每張獨立）

## Acceptance Criteria

- 點任何一張 photo → 出現 AdjustmentPanel，14+ sliders 都能拖
- 拖任何 slider 後 < 500ms 看到 preview 變化
- 「儲存為 preset」→ name 後 reload 仍在
- 「套用到全部」→ 進度條跑、處理完每張的 processed_paths.adjusted 都更新
- 套用過的 photo 在 PhotoGrid 上有「已調整」mark
- export zip 優先用 adjusted（若無）→ preset processed → 原圖

## Open Questions (need decisions before implementation)

1. **Live preview 渲染策略**：
   - (a) 純 server-side：每次 slider 拖完 debounce 300ms 打 API，small JPEG 回來。簡單、後端統一邏輯，但每次 ~200-500ms 延遲、多人 stack 互相 starve worker
   - (b) 純 client-side WebGL：CSS filter / Canvas 即時，但要 reimplement adjustment ops in JS / WebGL（雙份代碼，色彩可能不一致）
   - (c) hybrid：light ops 在 client（exposure / contrast / sat / temp 用 CSS filter），heavy ops（HSL / clarity / sharpening）回 server
   - **建議 (a)**：第一版 ship 速度優先，效能不夠再升 (c)

2. **HSL UI**：6 色 × 3 軸 = 18 sliders 太密。
   - (a) Lightroom 風格 tab 切 H/S/L 三組，每組 6 sliders → 共 18 但分頁顯示
   - (b) 6 色 row × 3 column grid
   - **建議 (a)**

3. **Preset scope**：自訂 preset 跨 project 還是只在 project 內？
   - 建議跨 project（晴晴的色調偏好通用）

4. **Adjustment 與 v0.2.0 pipeline 的關係**：
   - 套用 adjustment 之前要不要先跑 v0.2.0 pipeline (denoise / lens / level / crop)？
   - 建議 **adjustment 在 v0.2.0 pipeline 之後**：使用者先批次跑 preset → 滿意後再對個別有問題的張數做手動調整
   - 所以 source = `processed_paths[<preset>]` (若有) → fallback 原圖

## Estimated Scope

- Backend：~600 行（adjustments.py + 2 個 model + 1 個 router + migration）
- Frontend：~800 行（AdjustmentPanel + HslWheel + PresetManager + 整合 Preview.tsx）
- Tests：integration test for each op + preview latency assertion
- 工時估計：2-3 天 focused work

## Decision Required

簽核 4 個 open questions 後即可開工。先 ship v0.2.0（已 deploy），v0.3.0 拉分支實作。
