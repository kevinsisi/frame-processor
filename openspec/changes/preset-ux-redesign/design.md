## Context

Preview 頁的 manual adjustment + preset 工作流目前因詞彙混疊、狀態不可見、動作後果不可預期，導致使用者連最基本的「移除 preset」都做不到（實際抱怨：「我移除了 preset，照片還是有對比」）。詳細的混亂點解析、四個設計原則、UI mockup、實作分工估算詳見 `docs/superpowers/specs/2026-05-13-preset-ux-redesign-design.md`，本設計文件只擷取需要 OpenSpec 層級記錄的架構決策、風險、遷移、開放問題。

當前資料模型：照片有 `originals/` 原圖、`batch-v<N>/<photo>.jpg` AI 版本（v0.4.x immutable）、`manual-v<N>.jpg` 手動版本（v0.3.x），版本下拉指誰誰就是「目前這張」。`AdjustmentPreset` 是純 template、`photo_adjustments` 是 per-photo 草稿、`photo_adjustment_versions` 是已落地的手動版本紀錄。資料模型本身不需要變，問題純粹在 UI / vocabulary / 缺少 clear endpoint。

## Goals / Non-Goals

**Goals:**

- 落實四個設計原則（狀態永遠看得到、詞彙分家、動作後果可預期、清空微調明確存在）
- 把使用者原始抱怨「刪除 preset 但照片還有對比」這條路徑變成可達成的單一動作（透過新「清空照片微調」按鈕）
- AI 與手動兩條鏈的詞彙不再共用（preset / 產生 / 版本 不再有歧義）
- 不動 DB schema

**Non-Goals:**

- 不引入 `photo_adjustments.applied_preset_id` FK（違反 Lightroom 標準 preset 語意，使用者明確不要）
- 不做 cascade delete preset → photos
- 不融合 AI 版本與手動版本路徑
- 不做跨照片 preset 同步（preset 內容變了不會自動更新已套過的照片）
- 不做永久刪除已 archived 的 manual versions（v0.5.x 後續再評估）
- 不做 v0.6+ 的 preset bundle UI

## Decisions

### Decision 1: Preset 採 Lightroom 標準語意（template-only），不追蹤 applied state

**選項**：
- A. Preset 與照片解耦 — preset 是 template，載入 = 複製數值，照片狀態獨立。刪除 preset 不影響照片。
- B. Preset 是 first-class 「applied」 概念 — `photo_adjustments.applied_preset_id` FK，刪 preset 觸發 cascade reset 確認框。
- C. 混合 — 載入時複製數值但保留 preset_id 連結，使用者改 slider 自動 detach 成「自訂中」。

**決定**：A。

**理由**：使用者在 brainstorming 期間明確表態「preset 對使用者來說不就是快速設定某些設定嗎？」對應 Lightroom / Photoshop 業界標準。B 是我初版過度設計，C 也是。資料模型不動、UI 不暗藏複雜性 = 最低風險、最快交付，且永遠對得上使用者直覺。

### Decision 2: 「清空照片微調」是 archive 而非 delete

**選項**：
- A. Archive `photo_adjustment_versions`（檔案保留、`archived_at` 寫入、版本下拉跳過）。
- B. 真的刪除磁碟上 `manual-v<N>.jpg` + DB row。
- C. 兩種都提供（按鈕：archive；modal：永久刪除）。

**決定**：A。

**理由**：與 v0.4.x AI 版本的 archive 慣例一致（commit `3eba8e3`，`docs/adr/0003-batch-versioning.md`），可回滾、不會誤刪。`docs/superpowers/specs/2026-05-13-preset-ux-redesign-design.md` §8 列為開放問題，目前先採 A，v0.5.x 後續再評估是否補「永久刪除已 archived」入口。

### Decision 3: 新 endpoint 走 `POST /projects/{id}/adjustments/clear` 而非擴充既有 endpoint

**選項**：
- A. 新 endpoint `POST /projects/{id}/adjustments/clear`，body `{photo_ids: [...]}`。
- B. 把 reset 行為塞進既有 `POST /photos/{id}/adjustments`（傳 `clear=true` flag）。
- C. 在 `DELETE /adjustment-presets/{id}` 加 cascade 參數。

**決定**：A。

**理由**：清空照片微調 ≠ 套用空白微調 ≠ 刪除 preset。三件事語意不同，端點分開避免行為過載（CLAUDE.md「Fix root causes」「Avoid magic numbers / overloaded params」）。B 會讓 apply endpoint 多一條隱形分支；C 會把 preset endpoint 與 photo state 黏死，違反 Decision 1。

### Decision 4: Source chain 顯示在 BeforeAfter header 而不只在版本下拉

**選項**：
- A. BeforeAfter header 顯示「After: 手動 v2 — 基於 AI v1 / 展間白 · 對比 +25 / 色溫 +120」完整 source chain。
- B. 只在版本下拉的 option label 寫詳細名稱。
- C. 兩處都顯示但版本下拉精簡（v2）、header 完整。

**決定**：C，視 mobile 約束調整。

**理由**：使用者最痛點就是「看不到目前狀態」（原則 01），header 必須顯示足夠資訊讓使用者一眼看完，下拉作為切換入口維持精簡。Mobile 約束：source chain 可能超過螢幕寬度，fallback 為 `AI v1 + 手動 v2`（不展開 slider 摘要），desktop 才展開。詳見 `docs/superpowers/specs/2026-05-13-preset-ux-redesign-design.md` §8。

### Decision 5: 「主要偏離 sliders」的閾值

**選項**：
- A. 絕對值 ≥ 預設兩倍（例如預設 0，slider ≥ 2 顯示）。
- B. 絕對值 ≥ 預設的 10%（百分比閾值）。
- C. 固定數量（永遠顯示前 3 個最大偏離）。

**決定**：C，前 3 個最大絕對值偏離，避免任何一個 slider 都顯示時 header 爆炸。

**理由**：sliders 範圍不一（曝光 -5..+5、對比 -100..+100、HSL 各色 -50..+50），固定閾值（A、B）跨 slider 不公平。C 直接、可預期、不需 tuning。實機跑過若不夠用再加 secondary tier（例如「+ N 項微調」）。

## Risks / Trade-offs

- **[使用者誤以為「清空」會刪除磁碟檔案]** → 按鈕旁 hint 文明確寫「會封存（archive），不會永久刪除」，未來「⚙ 管理」modal 可加「永久刪除已封存版本」入口（v0.5.x 後續）。
- **[詞彙分家增加翻譯/維護成本]** → 第一版只有繁中，無 i18n；之後若加英文，把詞彙表（`docs/superpowers/specs/2026-05-13-preset-ux-redesign-design.md` §4.1）作為 i18n source of truth。
- **[BeforeAfter header 在 mobile 太擠]** → 響應式 fallback（見 Decision 4）。需要實機跑過確認。
- **[清空 endpoint 失敗中途，部分照片已 reset 部分沒]** → endpoint 使用 DB transaction 包住 reset + archive 兩步，全部成功才 commit；檔案 archive 慣例採「不真刪磁碟」，所以即使 DB rollback 後 archive flag 沒寫入，磁碟檔仍在、可重試。
- **[整合測試 deferred 到 `add-frame-test-harness`]** → 第一版優先 pure-function 服務層測試（reset 與 archive 邏輯），TestClient 端對端測試先列 deferred。風險：服務層邏輯與 router 串接的 bug 沒被 CI 抓到，靠手動 smoke 收尾。
- **[手動 vN archive 後使用者切版本下拉「想救回」]** → 第一版下拉不顯示 archived，與 v0.4.x AI 版本一致。後續可加「顯示已封存版本」勾選。
- **[使用者期待「清空已選 12 張」會自動跳出 toast 說「3 張沒微調已略過、9 張已清空」]** → endpoint response `{cleared_count: 9}` 由 FE 轉成 toast 文案。

## Migration Plan

- **Deploy 步驟**：純 forward-compatible，照常走 docker-publish + deploy-dev workflow，無 DB migration。
- **回滾策略**：純 FE 改名 + 新 endpoint，舊 endpoint 與 router 全保留。若 v0.5.0 部署後發現 critical regression，revert 該 commit 即可，無 schema 變更需要回滾。
- **使用者教育**：v0.5.0 release notes（ROADMAP 子版本條目）列詞彙對照表，第一次進 Preview 頁可考慮放一張一次性引導圖（v0.5.x 後續，不在本 change 範圍）。

## Open Questions

- 主要偏離 sliders 的 top-3 顯示是否實用？實機跑過 911 樣本與其他批次後確認。
- Mobile BeforeAfter header 的 fallback 字串是否需要進一步縮（例如「v2」而非「手動 v2」）？等實機 QA。
- Preset 管理 modal 要不要支援「重新命名」？第一版可只允許刪除 + name inline edit，看使用者需求。
- 「清空照片微調」action 是否也應同時自動切回 AI vN？目前 design 是切回最新非 archived 的 AI vN，若無則切回原圖。實機若覺得「切回原圖」太突兀，可改為「保持當前選擇但移除 manual overlay」。
