# v0.3.0 — Manual Adjustment Panel (Lightroom-style)

**Status**: proposed (awaiting sign-off — no code yet)
**Date**: 2026-05-07
**Author**: Kevin

## Why

v0.2.0 ship 後晴晴實際使用發現：preset + auto-pipeline 出來的結果 80% 場景 OK，但對特定光線（夕陽逆光、室內燈混色、夜拍車燈反光）需要手動微調才能上稿。每張車照重新跑一次 batch 太慢，需要 in-context 微調 → 即時預覽 → 滿意後再寫入 processed。

直接在 v0.2.0 內加 sliders 會把 v0.2.0 commit 變成「ship 不出去」的長線重構：sliders 是 14+ 參數 + HSL + live preview rendering pipeline，本身就需要架構決定（client-side WebGL vs server-side debounced render vs hybrid）。拆成獨立 v0.3.0 release。

## What Changes

### Backend (services + API)

新增 `services/adjustments.py`：純 Pillow 實作以下 ops，套用順序固定：

1. `white_balance_offset(image, temp, tint)` — 色溫（藍↔黃）+ 色調（綠↔洋紅）偏移
2. `orientation(image, degrees)` — 每張照片獨立 90 度左/右旋轉，Before/After 原圖側與 preview 側都立即套用
3. `manual_geometry(image, rotation, crop_zoom, crop_x, crop_y, distortion_x, distortion_y)` — 手動水平、裁切與水平/垂直透視修正，不呼叫 Gemini AI；legacy `distortion` payload 映射到 `distortion_x`
4. `exposure(image, ev)` — ±5 EV 線性增益
5. `contrast(image, amount)` — S-curve 對比
6. `highlights_shadows(image, hl, sh, whites, blacks)` — 4 通道 tone curve（Lightroom 風格）
7. `hsl(image, ranges)` — 紅/橙/黃/綠/藍/紫 6 個色相區間，每區間 H/S/L 各一個 slider（共 18 個 value）
8. `saturation(image, amount)` — 全域飽和
9. `vibrance(image, amount)` — 智慧飽和（保護已飽和區）
10. `clarity(image, amount)` — 中頻對比 / 柔化
11. `sharpness(image, amount)` — Lightroom 風格銳化

範圍：每個 slider `-100 ~ +100`（除了 EV 是 `-5 ~ +5`）。0 = no-op。

新增 `models/photo_adjustment.py:PhotoAdjustment` 表（一張 Photo 對應 0 或 1 組調整參數，JSON column 存 14+ 參數）。

新增 `models/adjustment_preset.py:AdjustmentPreset` 表（自訂 preset：name + JSON params + created_at + project_id 可空 = 全域 preset）。

新增 API：
- `POST /photos/{id}/adjustments` body 全套 14+ 參數 → 同步 render → 寫到 `processed/{photo_id}.adjusted.jpg`，回傳結果路徑
- `POST /photos/{id}/preview` body 同上 → **同步**回傳 small JPEG (long-edge 800px) 給 live slider
- `POST /projects/{id}/adjustments/apply` body params + photo_ids → 建立 `adjustment_jobs` worker job，逐張寫出 `adjusted` 並回報 progress
- Slider/rotation changes autosave as per-photo draft params in `photo_adjustments`; this does not create output versions.
- Generate/apply creates immutable manual versions in `photo_adjustment_versions` (`manual-vN.jpg`) and updates `processed_paths.adjusted` to the newest generated version.
- Photo cards expose version download selection: original, pipeline preset outputs, and manual vN outputs.
- Geometry controls use a dedicated visual editor window with a crop frame, drag/resize handles, and live preview of manual rotation plus horizontal/vertical perspective.
- `POST /adjustment-presets` 儲存 / `GET /adjustment-presets` 列出 / `DELETE /adjustment-presets/{id}`

### Frontend

- `web/src/components/AdjustmentPanel.tsx` — 14+ slider grid（按 Lightroom 分組：Light / Color / HSL / Detail）
- HSL 先在 `AdjustmentPanel` 內以 6 色相區間 H/S/L 三軌 slider 呈現
- `AdjustmentPanel` 提供儲存 / 載入 / 刪除自訂 preset
- live preview：slider drag → debounced 300ms → POST /preview → 換掉 BeforeAfter 的 after image
- live preview must render from a small preview image before expensive manual adjustments so rotation/color sliders feel immediate on mobile; full-resolution rendering is only for generated versions.
- "套用到已選照片" 按鈕 → 第一版前端逐張 POST apply；worker 進度條是下一步
- 單張選取 mode：在 PhotoGrid 上 click 一張 → 上方 BeforeAfter 立即載入該照片；AdjustmentPanel 編輯目前照片
- 每張照片卡片提供「下載處理後」單張下載；批次 zip 仍保留
- `showroom_white` 必須是中性 / 偏冷白，不可比原圖更暖

### Confirmed UX Revision (2026-05-08)

- Photo card version selector is not only a download selector. Selecting a version changes the displayed tile image, the top Before/After source, the manual adjustment base, and the single-photo download target for that photo.
- Version labels must use user-facing wording, not internal pipeline/state names. Avoid labels such as `adjusted`, `latest`, or raw preset keys.
- Top Before/After must behave as a large editing workspace. Desktop should prioritize a tall work area; mobile should keep the image area dominant and avoid shrinking into a small strip.
- Manual color-temperature and tint changes must be visually obvious in the live preview; do not use coefficients so subtle that a full slider move looks unchanged on a phone.
- Manual geometry is a full-screen single-photo editor, not a cramped two-column modal. It should show one large image, visible crop/level grid guides, direct crop-frame manipulation with fixed-ratio resize handles, bottom controls, live rotation/perspective preview, and explicit cancel/done actions.
- Batch pipeline defaults are: AI denoise = medium, wide-angle distortion correction checked, Gemini level correction checked, auto-crop aspect = original unless changed. Heavy remains available for explicit stronger cleanup but must not be the automatic/default choice.
- New uploads shown in Before/After before batch generation must be labeled as manual preview, not denoised output. If the active original has no generated preset output yet, show a clear CTA to run the batch pipeline.
- Heavy denoise must remain visible on extreme high-ISO/color-grain images even when NAFNet is unavailable or too conservative; medium/heavy denoise may combine NAFNet with OpenCV denoising, but the blend must be edge-aware so flat skies/dark backgrounds are cleaned strongly while structural detail, face contours, hair, and clothing folds are not globally smeared.
- If the current preset has no generated output for uploaded photos, Preview auto-starts a batch job from the current pipeline settings in the background. The Before side remains the undenoised original so denoise impact stays visible; the After side switches to generated output when the job completes.
- Batch detail restore applies thresholded unsharp mask after medium/heavy denoise and geometry, before color grade, to recover edges without re-amplifying flat-area noise.
- The lens correction toggle covers both radial barrel correction and automatic vertical perspective correction when Hough-detected side verticals converge upward.
- The batch "開始產生" action must stay visible in a sticky Preview summary of the current pipeline settings; pending/running jobs disable duplicate generation and pipeline controls.
- Upload-selected style must be persisted per project and become the Preview pipeline preset used by the processing panel, sticky action, and automatic generation payload.

### DB migration `0004_adjustment_panel.py`

新增 `photo_adjustments` + `adjustment_presets` 表；`Photo.processed_paths` 加 `"adjusted"` key 存最終手動調整輸出路徑。

## Non-Goals (defer)

- ❌ 局部調整（gradient mask / radial / brush）— Lightroom 高級功能，v0.4+
- ❌ 鏡頭校正自訂（v0.2 已有 lens distort，但係數不開放 UI）
- ❌ 噪點 NR + 細節保護的 advanced denoise（v0.2 NAFNet 強度 3 段已夠用）
- ❌ Camera profile（DCP）支援
- ❌ 局部調整的 per-area override（每張照片可以獨立微調，但不做同一張內的 brush / mask 區域調整）

## Acceptance Criteria

- 點任何一張 photo → 出現 AdjustmentPanel，14+ sliders 都能拖
- 點任何一張 photo → 上方 BeforeAfter 立即切換到該照片，不再固定第一張 processed sample
- 每張有處理結果的照片可單張下載 processed JPG
- `showroom_white` 輸出不會比原圖更暖，白色/灰色區域應維持中性或微冷
- 拖任何 slider 後 < 500ms 看到 preview 變化
- 「儲存為 preset」→ name 後 reload 仍在
- 「套用到全部」→ 進度條跑、處理完每張的 processed_paths.adjusted 都更新
- 使用者可先套用到全部，再切單張做獨立微調；單張 override 不影響其他照片
- 套用過的 photo 在 PhotoGrid 上有「已調整」mark
- export zip 優先用 adjusted（若無）→ preset processed → 原圖
- Photo card version dropdown changes the visible card image and active editing/download base for that photo.
- Pipeline defaults are medium denoise, lens distortion correction on, and level correction on.
- Before/After warns when the active original has no generated pipeline output yet, because AI denoise only runs after "開始產生".
- Before/After auto-generates missing preset outputs while preserving the original as the comparison baseline.
- Heavy denoise keeps flat regions clean while preserving architecture/body-line detail, and wide-angle correction visibly handles vertical perspective convergence in addition to barrel distortion.
- Primary batch start button is always easy to find via the sticky Preview settings/action summary and cannot be pressed again while a job is pending/running.
- Geometry editing opens as a full-screen single-image workspace with grid overlay guides, draggable/resizable crop frame, horizontal/vertical perspective controls, live transform preview, and cancel/done semantics.

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
