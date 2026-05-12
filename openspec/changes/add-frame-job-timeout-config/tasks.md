# Tasks — Configurable RQ job_timeout

## Config

- [ ] `api/config.py` 新增兩個 settings 欄位：
  - `rq_job_timeout_seconds_ai_batch: int = 1800`
  - `rq_job_timeout_seconds_adjustment_apply: int = 600`
- [ ] 對應環境變數 `RQ_JOB_TIMEOUT_SECONDS_AI_BATCH`、`RQ_JOB_TIMEOUT_SECONDS_ADJUSTMENT_APPLY`。
- [ ] 確認 settings instance 取得方式與既有 settings 一致（避免新建 cache layer）。

## 改 hardcode

- [ ] `api/routers/processing_jobs.py:127`：`job_timeout=1800` → `job_timeout=settings.rq_job_timeout_seconds_ai_batch`。
- [ ] `api/routers/adjustments.py:67`：同樣替換為 `rq_job_timeout_seconds_adjustment_apply`。
- [ ] 全文 grep `job_timeout=1800` 確認沒有其他殘餘。

## 加 log

- [ ] `processing_jobs.py` 建立 AI batch 後 `logger.info("ai batch job=%s photos=%d timeout=%ds", job.id, len(photo_ids), timeout)`。
- [ ] `adjustments.py` 對應 batch apply 加類似 info log。

## 測試

- [ ] 新增 `tests/test_job_timeout_config.py`：
  - 透過 monkeypatch settings 驗證 `processing_jobs.create_processing_job` 呼叫 `default_queue.enqueue` 時帶的 `job_timeout` 跟 setting 對齊（需 `add-frame-test-harness` 的 `fake_queue` fixture，本 change 依賴它）。
  - 同上 for `adjustments.py`。

## 文件

- [ ] README 補「RQ timeout 與 batch 大小」一節：何時要調大、調小、`deploy/.env` 怎麼覆寫。
- [ ] ARCHITECTURE.md 在 worker 段落補 timeout 概念。
- [ ] CLAUDE.md 若有 operational rule 段落，補「大 batch（>50 張）建議覆寫 timeout」。

## Verification

- [ ] `pytest -q tests/test_job_timeout_config.py` 全綠（依賴 harness change 落地後）。
- [ ] 本機 `pytest -q` 全綠。
- [ ] 對 production .env 範例補入新變數（若有 .env.example）。
