# Proposal: Per-Service Docs for chroma_clean / detail_preserve / cpl_look

## Summary

`ARCHITECTURE.md` § Pipeline 順序提到 chroma_clean、detail_preserve、cpl_look 三個 v0.4.x 新增的 batch step，但只在順序列表裡列名，沒有像既有的 `denoise` / `lens_distort` / `level_correct` 那樣的個別段落解釋「做什麼 / 何時觸發 / 失敗模式」。補齊到同樣的詳細度。

## Motivation

- 三支服務 v0.4.x 已 ship 並有對應 ADR / commit，但跨 session onboarding 仍要讀 service code 才能知道「Chroma Clean 是不是降噪？」、「Detail Preserve 會不會 hallucinate？」、「CPL Look 在哪個 strength 等於不啟用？」。
- 已有 docstring 散在 `services/chroma_clean.py`、`services/detail_preserve.py`、`services/cpl_look.py` 與 README 的長段描述，但 ARCHITECTURE.md 是 onboarding 的單一入口。
- ARCHITECTURE.md 是 RAG / 文件搜尋的主要目標，但目前對這三個服務只能命中「順序」段落而沒有實質定義。

## Scope

- 在 `ARCHITECTURE.md` § Pipeline 細節 / § Pipeline 順序之後或合適段落，補三個小節：
  - `chroma_clean`：暗部偽色雜訊修正。only chroma channel；保留 luma 不動；保護黃色安全帶 / Logo / 氛圍燈；NONE / LOW / MEDIUM / HIGH 對應強度與 dark-area 閾值。
  - `detail_preserve`：luma-only 高頻回填。把原圖可信亮度紋理塞回降噪後輸出；不生成不存在細節；NONE / LOW / MEDIUM / HIGH 對應 `amount` / `max_delta` / `structure_floor`。
  - `cpl_look`：拍後反光抑制（不等於 Adobe Reflection Removal）。針對車內鏡面飾板、儀表玻璃、中控螢幕、車窗反光；NONE / LOW / MEDIUM / HIGH 對應 `glare_reduction` / `sky_deepen` / `vibrance`。
- 每節包含：作用、何時 toggle on（建議的 strength default）、相依（誰跑在前 / 後）、失敗模式（什麼情況下會把照片做壞）、不負責的事（避免 PM 誤期）。
- 順手把 ROADMAP v0.4.0 phase 範圍區的三行 bullet 連到 ARCHITECTURE 對應 anchor。

## Non-Goals

- 不重寫整個 ARCHITECTURE.md。
- 不改 service 行為。
- 不寫 ADR；這三個服務的設計理由不夠關鍵到需要 ADR，個別段落 + docstring 就夠。
- 不補 i18n；中文敘述為主，沿用 ARCHITECTURE 既有風格。

## References

- `services/chroma_clean.py` 既有 docstring（domain knowledge 已在 code 裡）。
- `services/detail_preserve.py` docstring。
- `services/cpl_look.py` docstring。
- ROADMAP § v0.4.0 已記述子版本對應 commit。
