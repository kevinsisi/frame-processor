import type { AdjustmentParams, Photo, ProcessingVersion } from "@/types";
import { formatAIVersionLabel, formatBatchPresetLabel } from "@/utils/processingVersionLabel";

export interface SourceChainInput {
  photo: Photo;
  activeVersionValue: string | null;
  activeVersionLabel: string | null;
  processingVersions: ProcessingVersion[];
  liveDraftParams?: AdjustmentParams | null;
  isLiveDraft?: boolean;
}

export interface SourceChain {
  before: string;
  after: string;
  /** Top-3 slider deviations as `"對比 +25"` strings (already filtered). */
  sliderSummary: string[];
}

const SLIDER_LABELS: Record<string, string> = {
  exposure: "曝光",
  contrast: "對比",
  highlights: "亮部",
  shadows: "暗部",
  temperature: "色溫",
  tint: "色偏",
  saturation: "飽和",
  vibrance: "自然飽和",
  clarity: "清晰度",
  sharpness: "銳利化",
};

const SLIDER_KEYS: (keyof AdjustmentParams)[] = [
  "exposure",
  "contrast",
  "highlights",
  "shadows",
  "temperature",
  "tint",
  "saturation",
  "vibrance",
  "clarity",
  "sharpness",
];

export function buildSourceChain(input: SourceChainInput): SourceChain {
  const beforeLabel = "原圖";

  if (input.isLiveDraft && input.liveDraftParams) {
    const slider = topSliderDeviations(input.liveDraftParams);
    const aiLayer = describeAiLayer(input.photo, input.processingVersions);
    const layerSuffix = aiLayer ? `（基於 ${aiLayer}）` : "";
    return {
      before: beforeLabel,
      after: `目前微調預覽${layerSuffix}`,
      sliderSummary: slider,
    };
  }

  if (!input.activeVersionValue || input.activeVersionValue === "original") {
    return { before: beforeLabel, after: "原圖（尚未處理）", sliderSummary: [] };
  }

  if (input.activeVersionValue.startsWith("manual:")) {
    const manualId = input.activeVersionValue.slice("manual:".length);
    const version = (input.photo.adjustment_versions ?? []).find((v) => v.id === manualId);
    const versionLabel = version
      ? `手動 v${version.version_number}`
      : input.activeVersionLabel ?? "手動版本";
    const aiLayer = describeAiLayer(input.photo, input.processingVersions);
    const layerSuffix = aiLayer ? `基於 ${aiLayer}` : "基於 原圖";
    const slider = version ? topSliderDeviations(version.params) : [];
    return {
      before: beforeLabel,
      after: `${versionLabel} — ${layerSuffix}`,
      sliderSummary: slider,
    };
  }

  if (input.activeVersionValue.startsWith("processing:")) {
    const jobId = input.activeVersionValue.slice("processing:".length);
    const job = input.processingVersions.find((item) => item.id === jobId);
    const aiLabel = job ? formatAIVersionLabel(job) : input.activeVersionLabel ?? "AI 版本";
    return { before: beforeLabel, after: aiLabel, sliderSummary: [] };
  }

  if (input.activeVersionValue.startsWith("preset:")) {
    const preset = input.activeVersionValue.slice("preset:".length);
    return {
      before: beforeLabel,
      after: formatBatchPresetLabel(preset),
      sliderSummary: [],
    };
  }

  return {
    before: beforeLabel,
    after: input.activeVersionLabel ?? "未知版本",
    sliderSummary: [],
  };
}

function describeAiLayer(
  photo: Photo,
  processingVersions: ProcessingVersion[],
): string | null {
  const done = (photo.processing_versions ?? []).filter(
    (v) => v.status === "done" && Boolean(v.path),
  );
  if (done.length === 0) return null;
  const latest = done.reduce((prev, curr) => {
    const prevTime = prev.created_at ? Date.parse(prev.created_at) : 0;
    const currTime = curr.created_at ? Date.parse(curr.created_at) : 0;
    return currTime > prevTime ? curr : prev;
  });
  const job = processingVersions.find((item) => item.id === latest.processing_job_id);
  return job ? formatAIVersionLabel(job) : `AI v${latest.version_number}`;
}

export function topSliderDeviations(
  params: Partial<AdjustmentParams> | null | undefined,
  limit = 3,
): string[] {
  if (!params) return [];
  const candidates: { key: string; value: number; abs: number }[] = [];
  for (const key of SLIDER_KEYS) {
    const raw = (params as Record<string, unknown>)[key];
    if (typeof raw !== "number") continue;
    if (raw === 0) continue;
    candidates.push({ key, value: raw, abs: Math.abs(raw) });
  }
  candidates.sort((a, b) => b.abs - a.abs);
  return candidates.slice(0, limit).map(({ key, value }) => {
    const label = SLIDER_LABELS[key] ?? key;
    const formatted = value > 0 ? `+${formatNumber(value)}` : formatNumber(value);
    return `${label} ${formatted}`;
  });
}

function formatNumber(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(1);
}
