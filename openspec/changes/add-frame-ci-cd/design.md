## Context

`frame-processor` production runs on the `kevinhome` Windows desktop at Tailscale IP `100.83.112.20`. The live stack uses Docker Compose with five services: postgres, redis, api, worker, and web. Persistent production data was intentionally moved from Docker Desktop named volumes on C drive to G drive bind mounts:

- `G:/frame-processor/postgres-data`
- `G:/frame-processor/storage-data`
- `G:/frame-processor/redis-data`

The current deploy workflow is a placeholder, so production updates still depend on manual build/restart steps. The CI/CD design must publish Docker images, copy the compose file to the desktop, deploy by pulling images, and fail closed if the data mounts are missing or no longer point to G drive.

## Goals / Non-Goals

**Goals:**

- Use the HomeProject two-workflow pattern: Docker publish after `main` changes, then deploy after publish succeeds.
- Build `linux/amd64` images for the Windows desktop Docker runtime.
- Publish a dedicated CUDA worker image while keeping the API image CPU-only.
- Keep `deploy/docker-compose.yml` usable for local manual `docker compose up --build` while also supporting registry image pull in CD.
- Make deployment fail before `docker compose up` if the required G drive directories are missing or compose no longer uses G drive bind mounts.
- Make deployment fail after `docker compose up` if running containers use named volumes or non-G drive mount sources.
- Keep `GEMINI_MODEL` fixed to `gemini-2.5-flash`, keep `GEMINI_API_KEY` as an optional fallback instead of a deploy blocker, keep settings mutations protected by `SETTINGS_ADMIN_TOKEN`, and keep `KEY_MANAGER_URL` optional.

**Non-Goals:**

- Caddy routes `frame.sisihome.org` to `100.83.112.20:18533`; this avoids Windows/Hyper-V reboot-time excluded ranges that can cover `8533`.
- No database/storage migration; this change protects the existing G drive migration.
- No public exposure change; the service remains private to the existing HomeProject Tailscale/Caddy model.
- No new runtime dependency on key-manager.

## Decisions

### Docker images

Publish three images to Docker Hub:

- `kevin950805/frame-processor-api:<commit-sha>` plus `latest` using CPU torch
- `kevin950805/frame-processor-worker:<commit-sha>` plus `latest` using CUDA torch
- `kevin950805/frame-processor-web:<commit-sha>` plus `latest`

The `worker` compose service uses the dedicated worker image with `gpus: all` and a `python -m worker.main` command. Deploy verification confirms the worker container uses the worker image and sees CUDA before the release is considered healthy.

Alternative considered: keep reusing the API image for worker. That keeps builds smaller but leaves production AI batch processing on CPU-only torch and can silently waste the desktop GPU.

### Compose image and build compatibility

Each application service keeps both `image:` and `build:`. CD pulls the required images individually, then runs `docker compose up -d --pull never --no-build`, so it uses the published image without falling back to a local build. Local development can still run `cd deploy && docker compose up -d --build` from the repo checkout.

Alternative considered: remove `build:` from production compose. That would make CI/CD cleaner but would break the existing quick-start workflow that uses the same compose file from `deploy/`.

### Deploy path

CD copies `deploy/docker-compose.yml` to `D:/GitClone/_HomeProject/frame-processor/deploy/docker-compose.yml` on the desktop and runs compose from that directory. This matches the existing `deploy/.env` convention and avoids introducing a second production compose location.

Alternative considered: copy compose to the repo root. That would diverge from the existing `deploy/docker-compose.yml` quick-start and `.env` location.

### Remote PowerShell execution

CD uploads generated PowerShell scripts for env merge, pre-deploy validation, Docker Compose deployment, and post-deploy runtime verification, then invokes each script through `powershell -Command "& 'script.ps1' ..."`. This avoids multiline SSH command parsing differences between Bash, Windows OpenSSH, and PowerShell.

Alternative considered: keep large multiline PowerShell blocks directly in the SSH command. That can appear successful while only part of the command executes, leaving Docker containers on stale images.

### Environment strategy

The deploy workflow writes a host-side `.env` in the deploy directory from GitHub Actions secrets and constants:

- `DOCKERHUB_USERNAME`
- `IMAGE_TAG=<workflow_run.head_sha>` for automatic deploys
- `GEMINI_MODEL=gemini-2.5-flash`
- `GEMINI_API_KEY` optional fallback
- `SETTINGS_ADMIN_TOKEN`
- `KEY_MANAGER_URL` optional

The web image is built with `VITE_API_BASE_URL=/api`. The settings admin token remains a backend runtime secret; users can type it into the Settings page when needed instead of baking the token into the static web image.

Alternative considered: keep requiring `GEMINI_API_KEY` in GitHub secrets or desktop `.env`. That overfits deployment to an optional fallback secret even though the DB key pool is the preferred runtime key source.

### Volume guards

Pre-deploy guard checks:

- Required G drive directories exist.
- `docker compose config --format json` resolves postgres, redis, api, and worker volumes as `type=bind` with the expected G drive sources.

Post-deploy guard checks:

- `docker inspect` on running containers confirms mount type is `bind` and mount source normalizes to the expected G drive source.
- Any mount source normalizing to Docker Desktop's named volume path fails deployment.

Alternative considered: string search the compose file only. That catches obvious mistakes but cannot prove Docker Compose resolved the running mounts correctly.

## Risks / Trade-offs

- Missing required GitHub secrets block deployment -> fail fast with explicit required secret validation before writing `.env`; optional runtime fallbacks such as `GEMINI_API_KEY` must not block deployment.
- Docker Compose JSON output may vary by version -> keep validation focused on stable `services.*.volumes` fields and fail closed if parsing fails.
- Windows/Docker Desktop may report bind mount sources as Linux VM paths -> normalize known Docker Desktop host mount prefixes before comparing.
- Multiline remote shell parsing can skip intended Docker commands -> upload PowerShell scripts and execute script files instead of relying on inline multiline SSH strings.
- Windows SSH sessions may not have an interactive Docker credential-helper logon session -> generate a temporary Docker auth config from GitHub `DOCKERHUB_TOKEN`, upload it to the desktop deploy directory, copy it into a temp Docker config directory for explicit `docker pull` calls, then run `docker compose up --pull never` and clean up local/remote auth config files.
- The first worker image build is heavy because it installs CUDA torch/ultralytics -> use GitHub Actions build cache and publish only amd64 for the desktop target.
- Web image cannot receive runtime env after build -> do not bake `SETTINGS_ADMIN_TOKEN`; keep the Settings page manual-token path for admin mutations.

## Migration Plan

1. Add CI pytest and Docker build validation.
2. Add Docker publish workflow for api/worker/web images.
3. Update compose image fields while preserving build fields and G drive bind mounts.
4. Replace deploy scaffold with Windows desktop deploy workflow.
5. Update project docs and memory with the CI/CD contract.
6. Push to `main`; GitHub Actions builds images, then deploys to `100.83.112.20`.
7. Verify health at `http://100.83.112.20:18533/api/health` and final route `https://frame.sisihome.org/api/health`.

Rollback is manual but bounded: rerun deploy against the previous known-good Docker image tag or restore the previous compose file on the desktop. Persistent data remains on G drive and is not modified by the workflow.

## Open Questions

- None. Required runtime decisions are fixed by the existing HomeProject deployment standard and the G drive migration constraints.
