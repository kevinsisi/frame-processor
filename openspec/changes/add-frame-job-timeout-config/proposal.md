# Proposal: Make RQ job_timeout Configurable + Per-Photo Budget

## Summary

`api/routers/processing_jobs.py:127` 與 `api/routers/adjustments.py:67`（兩處）寫死 RQ `job_timeout=1800`（30 分鐘）。在大批次（100+ 張 4K 圖）+ worker 排隊 / GPU busy 的情境下不夠用，worker 被 RQ 強砍導致整批失敗只能走 retry-missing-only。改成可配置 + 內含「per-photo time budget」概念，並把預設值寫進 settings 而非 hardcode。

## Motivation

- v0.4.9 GPU split 後，GPU 推理本身快了，但偶有 GPU busy（multiple users / system load）的狀況下 1 張仍可能 60-90s，100 張就在 1800s 邊緣。
- 寫死 30 分鐘的問題不是「30 分鐘錯」而是「使用者沒法依場景調整」。
- 文件目前沒有任何地方說明 timeout 的存在；遇到問題只能讀 code 才知道。
- `adjustments.py:67` 也用 1800，但 adjustment apply batch（純像素操作）通常遠快於 AI batch，兩者用同一個值並不合理。

## Scope

- `api/config.py` 新增：
  - `RQ_JOB_TIMEOUT_AI_BATCH` 預設 1800
  - `RQ_JOB_TIMEOUT_ADJUSTMENT_APPLY` 預設 600（10 分鐘，adjustment 批次純像素 600s 已偏大）
  - `RQ_JOB_TIMEOUT_ZIP_EXPORT` 預設 600
  - 透過環境變數覆寫
- `processing_jobs.py:127` 與 `adjustments.py:67` 改讀 settings。
- 在 `processing_jobs.py` 建立 AI batch 時加 per-photo time budget log：`logger.info(...)` 印「N photos × 預估 X s = budget Y, RQ timeout = Z」，方便 PM / debug 時對照預期。
- README 與 ARCHITECTURE.md 補一節「RQ timeout 與 batch 大小」說明：何時要調大、調小、`deploy/.env` 怎麼覆寫。
- 不改 RQ 預設 `result_ttl` / `failure_ttl`，那是另一個議題。

## Non-Goals

- 不引入 batch 自動分片（把 100 張拆 4 個 25 張 job）；這是後續 capacity 議題，本 change 只解決 timeout 硬編碼。
- 不引入動態 timeout 估算（看歷史平均時間自動調）；first principle 是讓人能改，不是讓系統自動最佳化。
- 不改 worker 端的 graceful shutdown 邏輯。
- 不重設 timeout 計算單位（秒）；維持 RQ 慣例。

## References

- `api/routers/processing_jobs.py:127`
- `api/routers/adjustments.py:67`
- `api/config.py`（settings 結構與既有 env 變數 pattern）
- ROADMAP v0.4.0 phase（GPU worker split 後的容量觀察）
