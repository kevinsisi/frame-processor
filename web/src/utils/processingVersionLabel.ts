// Labels for AI batch processing versions and pipeline preset outputs.
// Kept as a standalone util so PhotoGrid.tsx doesn't carry a 200+ char inline
// template literal and so labels can be unit-tested without React.

import type { ProcessingVersion } from "../types";

export function presetLabel(preset: string): string {
  if (preset === "showroom_white") return "展示間白";
  if (preset === "outdoor_warm") return "戶外暖調";
  if (preset === "night_cold") return "夜拍冷調";
  return preset;
}

export function denoiseLabel(strength: string): string {
  if (strength === "none") return "不降噪";
  if (strength === "light") return "輕度降噪";
  if (strength === "medium") return "中度降噪";
  if (strength === "heavy") return "重度降噪";
  return strength;
}

export function cplLabel(strength: string): string {
  if (strength === "none") return "不做 CPL Look";
  if (strength === "low") return "CPL 輕度";
  if (strength === "medium") return "CPL 中度";
  if (strength === "high") return "CPL 重度";
  return strength;
}

export function chromaCleanLabel(strength: string): string {
  if (strength === "none") return "不修正偽色";
  if (strength === "low") return "偽色修正輕度";
  if (strength === "medium") return "偽色修正中度";
  if (strength === "high") return "偽色修正重度";
  return strength;
}

export function detailPreserveLabel(strength: string): string {
  if (strength === "none") return "不保留細節";
  if (strength === "low") return "細節保留輕度";
  if (strength === "medium") return "細節保留中度";
  if (strength === "high") return "細節保留重度";
  return strength;
}

export function aspectLabel(aspect: string): string {
  if (aspect === "original") return "原始比例";
  if (aspect === "ratio_3_2") return "3:2";
  if (aspect === "ratio_4_3") return "4:3";
  if (aspect === "ratio_16_9") return "16:9";
  if (aspect === "ratio_1_1") return "1:1";
  if (aspect === "ratio_9_16") return "9:16";
  return aspect;
}

export function jobStatusLabel(status: string): string {
  if (status === "pending") return "排隊中";
  if (status === "running") return "處理中";
  if (status === "done") return "完成";
  if (status === "failed") return "失敗";
  return status;
}

export function retryScopeLabel(scope: string): string {
  if (scope === "full") return "全批重試";
  if (scope === "missing_only") return "補缺重試";
  return scope;
}

// Minimal shape so callers can pass either a ProcessingVersion or any object
// with the same five strength/preset fields plus version_number. Helps the
// .cjs test fixture stay tiny.
export type AIVersionLabelInput = Pick<
  ProcessingVersion,
  | "version_number"
  | "preset"
  | "denoise_strength"
  | "chroma_clean_strength"
  | "detail_preserve_strength"
  | "cpl_strength"
>;

export function formatAIVersionLabel(job: AIVersionLabelInput): string {
  const parts = [
    presetLabel(job.preset),
    denoiseLabel(job.denoise_strength),
    chromaCleanLabel(job.chroma_clean_strength),
    detailPreserveLabel(job.detail_preserve_strength),
    cplLabel(job.cpl_strength),
  ];
  return `AI v${job.version_number}：${parts.join(" / ")}`;
}

export function formatAIVersionFallbackLabel(version_number: number): string {
  return `AI v${version_number}`;
}

export function formatBatchPresetLabel(preset: string): string {
  return `批次：${presetLabel(preset)}`;
}
