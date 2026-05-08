## Why

`frame-processor` 已經部署到 `frame.sisihome.org`，但目前 CI 只做基本 smoke check，部署 workflow 仍是 placeholder。每次 release 仍需要手動在 Windows desktop 上 build/restart，容易漏掉 compose 同步、Docker image publish、G 槽資料 bind mount 檢查，且可能讓 PostgreSQL/storage/Redis 回到 C 槽 Docker named volumes。

## What Changes

- 新增正式 Docker publish workflow，push `main` 時建置並發布 api/worker 共用 image 與 web image。
- 取代 placeholder dev deploy workflow，改為 Tailscale SSH 到 Windows desktop `100.83.112.20`，複製 `deploy/docker-compose.yml`，用臨時 Docker auth config 逐一 pull images 後執行 `docker compose up -d --pull never --no-build`，再跑 health check。
- 調整 production compose 支援 registry image 與 `${IMAGE_TAG}`，同時保留本機 build context 供手動開發使用。
- 在 CD 內加入部署前 guard：確認 `G:/frame-processor/postgres-data`、`G:/frame-processor/storage-data`、`G:/frame-processor/redis-data` 已存在，且 compose 內容明確使用 G 槽 bind mounts。
- 在 CD 內加入部署後 guard：用 `docker inspect` 驗證 postgres/api/worker/redis 的 mount source 仍是 `G:/frame-processor/...`，避免回退到 `/var/lib/docker/volumes/frame-processor_*`。
- 補強 CI，加入 `pytest tests` 與 Docker build validation。

## Capabilities

### New Capabilities
- `ci-cd-deployment`: frame-processor 的 Docker image publish、Windows desktop deployment、G drive persistent data guard 與 post-deploy health verification。

### Modified Capabilities
- None.

## Impact

- `.github/workflows/ci.yml`
- `.github/workflows/docker-publish.yml`
- `.github/workflows/deploy-dev.yml`
- `deploy/docker-compose.yml`
- Project deployment docs and memory for future release work
- GitHub Actions secrets and variables: Docker Hub credentials, Tailscale OAuth, deploy SSH key/user, Gemini fallback key, settings admin token
