# ADR 0002 — Bundled v0.2.0 Processing Pipeline

**Date**: 2026-05-07
**Status**: Accepted
**Supersedes**: ROADMAP v0.2 / v0.3 / v0.4 / v0.5 phasing

## Context

ROADMAP 原本將處理能力分四個 release：
- v0.2 — 純 Pillow 色調 preset
- v0.3 — NAFNet AI 降噪
- v0.4 — YOLO 自動裁剪
- v0.5 — Hough 水平校正

Walking skeleton (v0.1) 已驗證 stack 整條鏈通了。第一次嘗試把 v0.2 視為「色調 only」交付給晴晴使用時，重新檢視這個拆分是否合理。

## Decision

**把 v0.2 / v0.3 / v0.4 / v0.5 合併成一個 v0.2.0 release，並追加 lens distortion correction 階段。**

Pipeline 固定順序：`denoise → lens_distort → level_correct → auto_crop → color_grade`。

## Consequences

正向：
- 第一個交付的版本就是真正可用工具，不是半成品 demo
- 共用一套 ProcessingJob schema、worker job、FE 處理 UI，避免分四次重做
- 同一份 Docker image 拉一次 torch / opencv / ultralytics dependency
- v0.2 → v0.6 之間的 release 不會充滿「同 schema 重新 migrate」的 churn

負向：
- v0.2.0 變更面變大，code review / 測試成本集中在這次
- 引入較重相依（torch ~500MB CPU、opencv-headless ~50MB、ultralytics ~50MB），image 從 ~250MB 漲到 ~1GB
- NAFNet weights ~112MB lazy download，第一次處理會慢
- Gemini Vision 變成水平校正硬相依（沒 API key 就 fail）— 接受，因為 Hough Line 在實測車照場景表現不可靠

## Alternatives Considered

1. **照原 ROADMAP 分四次 release**：使用者前三個 release 拿到的都是不可用半成品，違反「給晴晴交付能用工具」的目標。否決。

2. **把水平校正改回 Hough Line**：實測車照常見場景（多斜線車身、停車格、室內地板）會被誤判，且 ±5° 上限會讓「歪 15° 的手機直拍」根本不校正。否決。

3. **把 NAFNet 推到 v0.3 但加 OpenCV NLM 在 v0.2**：兩種降噪要兩套 UI / schema 欄位，重複工。否決。

4. **GPU worker 拆 image**：v0.2.0 階段 throughput 不需要，CPU 推理 30 張在 5 分鐘內可接受。延後到實測證明 bottleneck 後再做。

## References

- OpenSpec change：`openspec/changes/2026-05-07-v0.2.0-processing-pipeline/`
- NAFNet 論文：Chen et al., "Simple Baselines for Image Restoration", ECCV 2022
- YOLOv8 model card：https://docs.ultralytics.com/models/yolov8/
