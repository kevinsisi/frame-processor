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
  if (strength === "none") return "不做 CPL";
  if (strength === "low") return "CPL 輕度";
  if (strength === "medium") return "CPL 中度";
  if (strength === "high") return "CPL 重度";
  return strength;
}

export function chromaCleanLabel(strength: string): string {
  if (strength === "none") return "不修正偽色";
  if (strength === "low") return "偽色輕度";
  if (strength === "medium") return "偽色中度";
  if (strength === "high") return "偽色重度";
  return strength;
}

export function detailPreserveLabel(strength: string): string {
  if (strength === "none") return "不保留細節";
  if (strength === "low") return "細節輕度";
  if (strength === "medium") return "細節中度";
  if (strength === "high") return "細節重度";
  return strength;
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
