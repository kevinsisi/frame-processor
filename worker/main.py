"""RQ worker entry：listen 在 ``default`` queue，處理目前定義的所有 job。

執行方式::

    python -m worker.main

job 模組透過 ``import worker.jobs`` 確保有被 register（RQ 用 string 路徑時不強制要求，
但這樣可以在 worker 啟動時先做一次 import-time 檢查）。
"""

from __future__ import annotations

from redis import Redis
from rq import Queue, Worker

import worker.jobs  # noqa: F401  確保 job 函數可被解析
from api.config import settings


def main() -> None:
    redis_conn = Redis.from_url(settings.redis_url)
    queue = Queue("default", connection=redis_conn)
    worker = Worker([queue], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
