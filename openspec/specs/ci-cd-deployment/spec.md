# ci-cd-deployment Specification

## Purpose
Define the frame-processor CI/CD contract for GitHub Actions validation, Docker image publishing, kevinhome self-hosted runner deployment, G drive data safety checks, runtime health verification, and deploy queue hardening.
## Requirements
### Requirement: Docker images are published for deployment
The system SHALL publish Docker images for `frame-processor-api`, `frame-processor-worker`, and `frame-processor-web` on push to `main` and on manual dispatch. The API image MUST use CPU torch, and the worker image MUST use CUDA torch for GPU-enabled batch processing.

#### Scenario: Main branch image publish
- **WHEN** changes are pushed to `main` for application code, Dockerfiles, compose, or CI/CD workflows
- **THEN** GitHub Actions builds `linux/amd64` images for api, worker, and web and pushes them to Docker Hub with the commit SHA tag plus a `latest` alias

#### Scenario: Worker uses CUDA worker image
- **WHEN** production compose resolves the worker service image
- **THEN** the image source is `frame-processor-worker` for the same commit SHA tag
- **AND** the worker service requests GPU access and starts `python -m worker.main`

### Requirement: CI validates backend, frontend, and container builds
The system SHALL run backend lint, backend import smoke checks, alembic offline migration checks, Python tests, frontend typecheck/build, and Docker image build validation before changes are accepted.

#### Scenario: Python tests are executed
- **WHEN** CI runs for a push or pull request
- **THEN** `python -m pytest tests` runs after dependencies are installed so repository packages are importable

#### Scenario: Docker build validation is executed
- **WHEN** CI runs for a push or pull request
- **THEN** api and web Docker images build successfully without pushing images

#### Scenario: Docker build context excludes local secrets
- **WHEN** Docker images are built locally or in CI
- **THEN** `.dockerignore` excludes `.env` files, deploy `.env` files, local data, caches, and generated frontend artifacts from the build context

### Requirement: Desktop deployment copies compose before applying changes
The system SHALL deploy to the Windows desktop at `100.83.112.20` from the kevinhome GitHub self-hosted runner by copying the repository `deploy/docker-compose.yml` to the desktop deploy directory before running Docker Compose locally.

#### Scenario: Self-hosted runner executes deployment locally
- **WHEN** the deploy workflow starts after a successful Docker publish or manual dispatch
- **THEN** GitHub Actions schedules the job on the kevinhome self-hosted runner with `self-hosted`, `Windows`, `X64`, and `frame-processor-prod` labels
- **AND** the workflow executes Docker and PowerShell commands locally on the Windows desktop instead of using SSH

#### Scenario: Deploy workflow syncs compose
- **WHEN** the deploy workflow starts after a successful Docker publish or manual dispatch
- **THEN** it creates `D:/GitClone/_HomeProject/frame-processor/deploy` if needed and copies `deploy/docker-compose.yml` to `D:/GitClone/_HomeProject/frame-processor/deploy/docker-compose.yml`

#### Scenario: Deploy workflow applies published images
- **WHEN** compose has been copied and pre-deploy guards pass
- **THEN** the workflow pulls the published commit SHA images and recreates postgres, redis, api, worker, and web without local builds
- **AND** desktop pulls use a temporary Docker auth config generated from GitHub `DOCKERHUB_TOKEN` so the Windows Docker credential helper is not required
- **AND** Docker Compose is applied with `up -d --pull never --force-recreate --no-build --remove-orphans postgres redis api worker web` after the explicit image pulls succeed
- **AND** temporary Docker auth config files are removed after deployment attempts

#### Scenario: Deploy queue is bounded
- **WHEN** multiple desktop deploys are triggered while a deploy is still running
- **THEN** the workflow serializes them with a production deploy concurrency group and does not cancel the in-progress deploy
- **AND** the deploy job has a bounded 60-minute timeout so a Docker Desktop stall cannot occupy the self-hosted runner indefinitely

#### Scenario: Stale Docker auth configs are cleaned
- **WHEN** a deploy begins or finishes after an earlier interrupted deploy
- **THEN** the workflow removes stale `frame-processor-docker-config-*` temp directories from the runner temp path without printing Docker credentials

### Requirement: Deployment fails closed when G drive data paths are unsafe
The system SHALL refuse to deploy before `docker compose up` if required G drive persistent data directories are missing or if compose does not resolve postgres, redis, api, and worker storage as G drive bind mounts.

#### Scenario: Required G drive directories are missing
- **WHEN** any of `G:/frame-processor/postgres-data`, `G:/frame-processor/storage-data`, or `G:/frame-processor/redis-data` does not exist on the desktop
- **THEN** the deploy workflow fails before running `docker compose up`

#### Scenario: Compose resolves to non-G-drive storage
- **WHEN** Docker Compose config for postgres, redis, api, or worker resolves storage to a named volume or a source other than the expected `G:/frame-processor/...` path
- **THEN** the deploy workflow fails before running `docker compose up`

### Requirement: Deployment verifies runtime mounts and health
The system SHALL verify running container images, mounts, and the web-proxied health endpoint after deployment.

#### Scenario: Runtime mount verification succeeds
- **WHEN** `docker compose up -d` completes
- **THEN** `docker inspect` confirms postgres, redis, api, and worker mounts are bind mounts whose normalized sources are the expected G drive paths

#### Scenario: Runtime image verification succeeds
- **WHEN** `docker compose up -d` completes
- **THEN** `docker inspect` confirms api, worker, and web containers use the expected commit SHA image tag
- **AND** the worker container uses the dedicated `frame-processor-worker` image

#### Scenario: Worker CUDA verification succeeds
- **WHEN** runtime image and mount verification passes
- **THEN** the deploy workflow executes a worker-container CUDA smoke check
- **AND** deployment fails unless `torch.cuda.is_available()` returns `True`

#### Scenario: Named volume regression is detected
- **WHEN** any inspected frame-processor container mount source normalizes to Docker Desktop named volume storage or a non-G-drive path
- **THEN** the deploy workflow fails and reports the unsafe mount

#### Scenario: Health check succeeds
- **WHEN** runtime mount verification passes
- **THEN** the workflow polls `http://100.83.112.20:18533/api/health` until it returns the expected app version or the retry budget is exhausted

### Requirement: Runtime secrets and optional integrations remain constrained
The system SHALL keep Gemini model selection, settings admin protection, and key-manager integration aligned with production rules.

#### Scenario: Gemini model is fixed
- **WHEN** the deploy workflow writes runtime environment values
- **THEN** `GEMINI_MODEL` is set to `gemini-2.5-flash`

#### Scenario: Settings mutations remain protected
- **WHEN** `/settings` mutation endpoints are used after deployment
- **THEN** the backend requires `SETTINGS_ADMIN_TOKEN` and the workflow does not commit or print the token

#### Scenario: Desktop env secrets are preserved
- **WHEN** `GEMINI_API_KEY`, `SETTINGS_ADMIN_TOKEN`, or `KEY_MANAGER_URL` are not provided as GitHub Actions secrets
- **THEN** the deploy workflow keeps the existing desktop `deploy/.env` values instead of replacing them with empty strings

#### Scenario: Required runtime secret is present after env merge
- **WHEN** the deploy workflow merges CI-provided env values with the desktop `deploy/.env`
- **THEN** deployment fails before Docker Compose if `SETTINGS_ADMIN_TOKEN` is missing from the merged env file
- **AND** `GEMINI_API_KEY` remains an optional runtime fallback because the DB key pool is the preferred source

#### Scenario: Settings token is not baked into web image
- **WHEN** the web Docker image is built for CI/CD or local compose builds
- **THEN** the web Dockerfile does not define `VITE_SETTINGS_ADMIN_TOKEN` and `SETTINGS_ADMIN_TOKEN` remains api/worker runtime-only

#### Scenario: Key manager remains optional
- **WHEN** `KEY_MANAGER_URL` is empty
- **THEN** frame-processor still deploys and runs without requiring key-manager
