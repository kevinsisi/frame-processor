import type {
  AspectRatio,
  ChromaCleanStrength,
  ColorGradePreset,
  CplStrength,
  DetailPreserveStrength,
  DenoiseStrength,
  ProcessingJobCreate,
  ProcessingVersion,
} from "../types";

export const DEFAULT_PIPELINE_PRESET: ColorGradePreset = "showroom_white";
export const DEFAULT_PIPELINE_DENOISE: DenoiseStrength = "medium";
export const DEFAULT_PIPELINE_CPL: CplStrength = "none";
export const DEFAULT_PIPELINE_CHROMA_CLEAN: ChromaCleanStrength = "medium";
export const DEFAULT_PIPELINE_DETAIL_PRESERVE: DetailPreserveStrength = "low";
export const DEFAULT_PIPELINE_LENS_DISTORT = false;
export const DEFAULT_PIPELINE_LEVEL_CORRECT = false;

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
  cplStrength: CplStrength;
  chromaCleanStrength: ChromaCleanStrength;
  detailPreserveStrength: DetailPreserveStrength;
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
    cpl_strength: settings.cplStrength,
    chroma_clean_strength: settings.chromaCleanStrength,
    detail_preserve_strength: settings.detailPreserveStrength,
  };
}

export function pipelinePayloadMatchesVersion(
  version: ProcessingVersion,
  payload: ProcessingJobCreate,
): boolean {
  return (
    version.preset === payload.preset &&
    version.denoise_strength === (payload.denoise_strength ?? "none") &&
    version.lens_distort_correct === (payload.lens_distort_correct ?? false) &&
    version.level_correct === (payload.level_correct ?? false) &&
    version.auto_crop_aspect === (payload.auto_crop_aspect ?? null) &&
    version.cpl_strength === (payload.cpl_strength ?? "none") &&
    version.chroma_clean_strength === (payload.chroma_clean_strength ?? "none") &&
    version.detail_preserve_strength === (payload.detail_preserve_strength ?? "none")
  );
}
