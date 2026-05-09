## 1. Compose And Image Publishing

- [x] 1.1 Add production image names and `${IMAGE_TAG}` support to `deploy/docker-compose.yml` while preserving local `build:` blocks and G drive bind mounts.
- [x] 1.2 Add `.github/workflows/docker-publish.yml` to build and push amd64 api and web images to Docker Hub.
- [x] 1.3 Add `.dockerignore` so Docker build context excludes local env files, caches, data, docs, and generated frontend artifacts.

## 2. CI Validation

- [x] 2.1 Update `.github/workflows/ci.yml` to install pytest and run `pytest tests`.
- [x] 2.2 Add CI Docker build validation for api and web images without pushing.

## 3. Desktop Deployment

- [x] 3.1 Replace `.github/workflows/deploy-dev.yml` scaffold with a Tailscale SSH deploy workflow for `100.83.112.20`.
- [x] 3.2 Make the deploy workflow copy `deploy/docker-compose.yml` to `D:/GitClone/_HomeProject/frame-processor/deploy/docker-compose.yml`.
- [x] 3.3 Make the deploy workflow write runtime `.env` values from GitHub Actions secrets without logging secrets.
- [x] 3.4 Add pre-deploy guards for required G drive directories and compose-resolved bind mounts.
- [x] 3.5 Add post-deploy `docker inspect` mount verification and `http://100.83.112.20:18533/api/health` health check.

## 4. Documentation And Memory

- [x] 4.1 Update project deployment docs/rules with the new CI/CD contract and required secrets.
- [x] 4.2 Update HomeProject memory with the frame-processor CI/CD deployment facts.

## 5. Verification And Release

- [x] 5.1 Run frontend typecheck/build, backend lint/tests/compile, and Docker build validation locally where feasible.
- [x] 5.2 Run Gemini pre-commit review and fix any findings.
- [x] 5.3 Commit with the required co-author line and push to `main`.
- [ ] 5.4 Track GitHub Actions publish/deploy results and verify the deployed health endpoint.
