import type {
  AspectRatio,
  ColorGradePreset,
  DenoiseStrength,
  ProcessingJobCreate,
} from "../types";

export const DEFAULT_PIPELINE_PRESET: ColorGradePreset = "showroom_white";
export const DEFAULT_PIPELINE_DENOISE: DenoiseStrength = "medium";

const COLOR_GRADE_PRESETS: ColorGradePreset[] = [
  "showroom_white",
  "outdoor_warm",
  "night_cold",
];

type StorageLike = Pick<Storage, "getItem" | "setItem">;

export interface PipelineSettingsState {
  preset: ColorGradePreset;
  denoise: DenoiseStrength;
  lensDistort: boolean;
  levelCorrect: boolean;
  aspect: AspectRatio;
}

export function isColorGradePreset(value: string | null): value is ColorGradePreset {
  return COLOR_GRADE_PRESETS.includes(value as ColorGradePreset);
}

export function pipelinePresetStorageKey(projectId: string): string {
  return `frame-processor:style:${projectId}`;
}

export function readProjectPipelinePreset(
  projectId: string,
  storage: StorageLike | null = typeof window === "undefined" ? null : window.localStorage,
): ColorGradePreset | null {
  if (!storage) return null;
  try {
    const stored = storage.getItem(pipelinePresetStorageKey(projectId));
    return isColorGradePreset(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function writeProjectPipelinePreset(
  projectId: string,
  preset: ColorGradePreset,
  storage: StorageLike | null = typeof window === "undefined" ? null : window.localStorage,
): void {
  if (!storage) return;
  try {
    storage.setItem(pipelinePresetStorageKey(projectId), preset);
  } catch {
    // Private mode/quota failures should not block processing.
  }
}

export function buildPipelinePayload(settings: PipelineSettingsState): ProcessingJobCreate {
  return {
    preset: settings.preset,
    denoise_strength: settings.denoise,
    lens_distort_correct: settings.lensDistort,
    level_correct: settings.levelCorrect,
    auto_crop_aspect: settings.aspect === "original" ? null : settings.aspect,
  };
}
