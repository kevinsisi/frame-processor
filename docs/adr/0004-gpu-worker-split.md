# ADR 0004 — Split AI Batch Worker onto Dedicated CUDA Image

**Date**: 2026-05-12
**Status**: Accepted
**Supersedes**: ADR 0002 § Alternatives Considered #4（「v0.2.0 不拆 GPU worker，先用 CPU 推理」）

## Context

v0.2.0 ADR 0002 把 GPU worker split 延到「實測證明 bottleneck 後再做」。實際跑了三個月後測量：

- CPU 推理 NAFNet-SIDD-width32（單 RTX 4070 對照組）：30 張 × 4K 圖大約 8-12 分鐘
- 同硬體跑 GPU 推理：30 張同樣的圖 < 90 秒
- 晴晴實際使用 batch 通常 50-100 張，CPU pipeline 要 15-30 分鐘，已超過 RQ 30 分鐘 `job_timeout`，導致中段 worker 被砍掉，必須走 retry-missing-only 才能補完
- API container 不需要 GPU；只有 worker 跑 NAFNet / YOLO 推理時需要

桌機部署環境（kevinhome runner）有 RTX 4070，但 v0.2.0 階段的單一 `frame-processor-api:latest` image 同時跑 API + worker，使得：
- API container 不需要的 CUDA runtime 也被一起塞進去（image 變大）
- 想單獨重新部署 API（修 bug、調 nginx）會牽動 worker，反之亦然

## Decision

**API 與 AI batch worker 拆成兩個 Docker image，共用同一份 `deploy/api.Dockerfile` + 不同 `TORCH_WHEEL_INDEX` build arg；docker-compose 把 worker service 配 `gpus: all`；部署後驗證 `torch.cuda.is_available()` 為 true，否則部署失敗。**

具體做法：

- `deploy/api.Dockerfile` 接受 build arg `TORCH_WHEEL_INDEX`：
  - `kevin950805/frame-processor-api:<sha>` 用 `https://download.pytorch.org/whl/cpu` 建
  - `kevin950805/frame-processor-worker:<sha>` 用 `https://download.pytorch.org/whl/cu126` 建
- `.github/workflows/docker-publish.yml` matrix 兩個 build target，同一份 Dockerfile 兩種 wheel index。
- `.github/workflows/deploy-dev.yml` 把 worker container 起來後在 container 內跑 `python -c "import torch; assert torch.cuda.is_available()"`，回非 0 就 fail deploy。
- `deploy/docker-compose.yml`：worker service 加 `deploy.resources.reservations.devices: [{driver: nvidia, count: all, capabilities: [gpu]}]` 與 `gpus: all`（runtime 旗標兩寫，兼容 Docker Compose 與 nvidia-runtime）。

## Consequences

正向：

- 50-100 張 batch 從 15-30 分鐘掉到 2-5 分鐘，落在 RQ 30 分鐘 timeout 內，retry-missing-only 流程從「天天用」變「偶爾才需要」。
- API image 不背 CUDA runtime，重新部署 API 不會牽動 worker（image 約 1.5GB → CPU 版約 900MB）。
- 部署時的 CUDA preflight 強制要求 GPU 真的能用；以前 CPU fallback 會偽裝成「成功」結果跑超慢沒人發現。
- 未來如果要拆出第二台 GPU node、或加 cloud GPU worker，現在的拆法已經支援。

負向：

- CI build 時間從 1 個 image build 變兩個 image build（CPU + CUDA），每次 push 多花 ~3 分鐘。
- 沒 GPU 的部署環境無法跑 worker。**這是有意的**：與其讓使用者拿到「批次跑很慢但沒人警告」的 CPU fallback，不如部署當下就 fail，讓使用者知道環境不對。
- GPU driver / CUDA runtime 版本要跟著 PyTorch wheel index 鎖定（目前 cu126），driver 升級必須同步更新 wheel。
- 桌機 runner 的 nvidia driver 要維護到能跑 CUDA 12.6 toolkit；如果 driver 突然 broken，整個 worker 起不來。

## Alternatives Considered

1. **同一個 image 同時支援 CPU / CUDA wheel，runtime detect 後選用**：
   - 否決：image 體積會雙倍肥（兩套 torch wheel），且 `torch.cuda.is_available()` 在錯誤 driver 配置下會 false 但 wheel 還是 CUDA 版，會 import error。

2. **保留 CPU fallback，warning 之後繼續跑**：
   - 否決：問題就是 CPU 跑得太慢沒人發現。明示 fail > 暗自降級。

3. **改用 ROCm 支援 AMD GPU**：
   - 否決：當下 production runner（kevinhome）是 NVIDIA RTX 4070；ROCm 還沒測過；不在此 phase 範圍。

4. **用 Docker buildx `--platform`**：
   - 否決：跟 GPU/CPU 拆無關，那是處理 ARM/x86 cross-build。

5. **CUDA 12.1 / 11.8 wheel**：
   - 否決：目前 PyTorch nightly 主力是 cu126；cu121 / cu118 比較舊但部署 host 的 driver 已更新到 545+ 支援 12.6；沒理由用舊 wheel。

## References

- OpenSpec change：`openspec/changes/add-frame-ci-cd/`（GPU worker 部分）
- ROADMAP § v0.4.0 — AI Batch Versioning & Quality（v0.4.9 子版本）
- 相關 commit：`1e7a38a feat: run AI worker on GPU`、`293e61e docs: clarify geometry correction usage`
- ADR 0002 § Alternatives Considered #4（被本決議取代）
- PyTorch CUDA wheels：https://pytorch.org/get-started/locally/
