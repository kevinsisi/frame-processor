# ADR 0003 — AI Batch Versioning & Immutable Output Paths

**Date**: 2026-05-10
**Status**: Accepted
**Supersedes**: v0.2.x 「同一 preset 直接覆蓋 processed file」

## Context

v0.2.x 的批次輸出路徑是 `processed/<photo>.<preset>.jpg`，同一張照片重跑同一個 preset 會直接覆蓋舊輸出。實際使用後出現幾個問題：

1. **沒法 A/B 比較**：使用者調整 pipeline 設定（例如把 denoise 從 medium 調到 heavy）重跑後，再也看不到舊版輸出，沒法當場肉眼比較哪個比較好。
2. **失敗的批次拖累成功路徑**：worker 跑到一半某張照片失敗，整批寫入路徑同時混入新舊版本，使用者下載 zip 時拿到混合狀態。
3. **沒法重試「只跑沒成功的那幾張」**：失敗的照片重跑後，成功的照片會被一起覆蓋掉，等於把整批的進度灌掉。
4. **沒有審計**：「這張照片現在的處理結果是哪一次跑出來的？」沒有 metadata 可以回答。

PM (晴晴) 在實際用 v0.2.x 試了一週後明確要求「我想看每次按下『開始產生』的版本，跟之前那次比，必要時可以指定下載第幾版」。

## Decision

**引入 `AI vN` 批次版本概念，每次按「開始產生」建立一個 immutable 版本。**

具體模型：

- `ProcessingJob.version_number`：每個 project 內 monotonic 遞增（`uq_processing_job_project_version` unique constraint）。第一個 batch = v1。
- `ProcessingJob.archived_at`：使用者可以隱藏（archive）已完成或失敗的版本，但不刪檔。
- `ProcessingJob.retry_scope` ∈ {`none`, `full`, `missing_only`}：標示這個版本是不是重跑、是完整重跑還是只補缺漏。
- `ProcessingJob.retry_of_job_id`：指向被重跑的源 version，建立版本鏈。
- 新增 `photo_processing_versions` 表逐張記錄狀態（`pending` / `running` / `done` / `failed`）+ error message，讓「部分成功」狀態可以準確 expose。
- 輸出路徑 `processed/<photo>.batch-vN.jpg` immutable，同 preset 不同 version 共存於 disk。
- `Photo.processed_paths[preset]` 作為「最新成功且未封存版本」的相容 cache，archive 時即時 recompute。

API contract：

- `POST /projects/{id}/process` 同 project 有 in-flight pending/running 版本時回 409，除非 `force=true`（user 明確要平行兩個版本）。
- `DELETE /processing-jobs/{id}/version` 對 done / failed 版本做 archive，running 中的版本拒絕（409）。
- 失敗 / 部分版本不會 silent fallback 到舊版本，前端拿到 `status=failed` + error 顯示。

## Consequences

正向：

- 使用者可以同時看到 AI v1 / v2 / v3，隨時切回去比較。
- 部分失敗的批次可走 retry-missing-only flow，不毀掉已成功的照片。
- Export zip 可指定版本下載，不會混入舊輸出。
- 審計：每張照片有完整 processing history。
- failed 版本不會被當沒事，使用者看得到「這張這次沒成功，error 是 X」。

負向：

- Disk usage 線性成長：N 張 × M 次重跑 = N×M 份 JPEG。沒有 retention policy 是時間炸彈；目前依賴使用者手動 archive。
- `processed_paths[preset]` cache 與 `photo_processing_versions` 的一致性要靠 archive 時 recompute；race 風險在「兩個並發 archive」時可能丟字段，已在 code review 階段標 risk 但沒擋。
- `version_number` 計算用 `MAX(version_number) + 1` 在 high-concurrency 下可能撞 unique constraint，現在靠 409 duplicate-blocking 把問題卡掉。
- Export / 下載介面複雜度上升：要支援 selected version 路由 + missing-output 409。
- frontend 卡片版本下拉、Before/After 切換、AI version switcher 都要對齊到同一份 version state（已實作但 reusable cost 不低）。

## Alternatives Considered

1. **保留覆蓋語意 + 加 client-side history**：用 IndexedDB 存「最近 3 個版本的縮圖」。
   - 否決：縮圖不是原解析度，沒法當下載目標；本機資料跨裝置不同步；使用者明確要的是 server-side immutable 版本。

2. **每次 process 開新 ProcessingJob 但共用 `processed/<photo>.<preset>.jpg`**：
   - 否決：等於沒解決核心問題；只是讓 job table 變肥。

3. **單一全域 version_number（不依 project）**：
   - 否決：晴晴的 mental model 是「每個 project 各自從 v1 算」；全域編號（例如 v347）對她沒意義。

4. **soft delete 走 `deleted_at` 而不是 `archived_at`**：
   - 否決：archive 不等於 delete，使用者可能改變心意把 archive 過的版本再 unarchive。命名上 `archived_at` 比 `deleted_at` 更貼切。

5. **path 用 commit-style hash (`processed/<photo>.<sha>.jpg`)**：
   - 否決：sha 對使用者不可讀；`batch-v3` 比 `batch-7a3f9c` 友善很多；project-internal monotonic 對 onboarding 也比較好理解。

## References

- OpenSpec change：`openspec/changes/2026-05-10-batch-version-control/`
- ROADMAP § v0.4.0 — AI Batch Versioning & Quality
- 相關 alembic migration：`alembic/versions/0007_batch_versions.py`
- API：`api/routers/processing_jobs.py`、`api/routers/projects.py::_processing_version_out`
- Cache 一致性：`services/processing_versions.py::recompute_latest_processed_cache`
