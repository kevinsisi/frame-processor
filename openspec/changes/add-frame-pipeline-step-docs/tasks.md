# Tasks — Per-Service Docs for v0.4.x Pipeline Steps

Status note (2026-05-16): `ARCHITECTURE.md` already documents the three steps in the pipeline diagram, settings table, and ordering rationale. Remaining work is the fuller per-service sections requested by this change.

## Drafting

- [x] `ARCHITECTURE.md` 已有 `chroma_clean` / `detail_preserve` / `cpl_look` 的 pipeline diagram、設定欄位與順序理由。
- [ ] 讀過 `services/chroma_clean.py` / `services/detail_preserve.py` / `services/cpl_look.py` 的 module docstring 與 `_Profile` 設定，整理成一致格式。
- [ ] 對齊既有 ARCHITECTURE.md 段落（denoise / lens_distort / level_correct）標題層級與長度。

## 寫入

- [ ] `ARCHITECTURE.md` 補 `### chroma_clean` 段落：作用、何時用、強度檔位、相依、失敗模式、不做的事。
- [ ] `ARCHITECTURE.md` 補 `### detail_preserve` 段落：同上模板。
- [ ] `ARCHITECTURE.md` 補 `### cpl_look` 段落：同上模板。
- [ ] ROADMAP v0.4.0 phase 範圍區的三支 bullet 連結到 ARCHITECTURE 對應 anchor（或直接引用段落標題）。
- [ ] CLAUDE.md 若有提到「pipeline 三新 step」的相關說明，更新交叉引用。

## 額外完成（範圍外，但已在 2026-05-18 直接寫入）

- [x] `ARCHITECTURE.md` 補 `### color_grade` 段落：`_showroom_white` 函數鏈全表（步驟 1~13）、設計禁忌（gradient cap masking 禁用原因、dither 必保持啟用）、3+ 次連續 fix 的架構質疑原則。此段落是 v0.5.11~v0.5.19 髒污斑塊事故的事後文件化。

## Verification

- [x] grep `ARCHITECTURE.md` 確認三個 step 名稱已存在。
- [ ] 確認三個完整新段落存在且字數對齊既有段落（chroma_clean / detail_preserve / cpl_look 尚未補）。
- [ ] 確認沒有重複內容；避免 ROADMAP / README / ARCHITECTURE 三邊重複描述。
- [ ] PR / commit 包含 ARCHITECTURE diff，commit message 點明三個段落已補。
