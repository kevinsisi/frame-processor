import { missingPipelineOutputPhotoIds, needsPipelineRunNote } from "../src/utils/pipelinePreview.js";
import {
  DEFAULT_PIPELINE_DENOISE,
  DEFAULT_PIPELINE_CHROMA_CLEAN,
  DEFAULT_PIPELINE_CPL,
  buildPipelinePayload,
  isColorGradePreset,
  pipelinePresetStorageKey,
  readProjectPipelinePreset,
  writeProjectPipelinePreset,
} from "../src/utils/pipelineSettings.js";

function assertEqual(actual: boolean, expected: boolean, label: string): void {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

assertEqual(
  needsPipelineRunNote({
    sourceKind: "original",
    hasMatchingPipelineOutput: false,
    hasActivePreview: true,
  }),
  true,
  "original without output shows note",
);

assertEqual(
  needsPipelineRunNote({
    sourceKind: "original",
    hasMatchingPipelineOutput: true,
    hasActivePreview: true,
  }),
  false,
  "existing pipeline output hides note",
);

assertEqual(
  needsPipelineRunNote({
    sourceKind: "preset",
    hasMatchingPipelineOutput: false,
    hasActivePreview: true,
  }),
  false,
  "non-original source hides note",
);

assertEqual(
  needsPipelineRunNote({
    sourceKind: "original",
    hasMatchingPipelineOutput: false,
    hasActivePreview: false,
  }),
  false,
  "preview not loaded hides note",
);

const missing = missingPipelineOutputPhotoIds(
  [
    { id: "a", processed_paths: {} },
    { id: "b", processed_paths: { showroom_white: "b.jpg" } },
    { id: "c", processed_paths: { night_cold: "c.jpg" } },
  ],
  "showroom_white",
);

if (missing.join(",") !== "a,c") {
  throw new Error(`missingPipelineOutputPhotoIds: expected a,c, got ${missing.join(",")}`);
}

if (DEFAULT_PIPELINE_DENOISE !== "medium") {
  throw new Error(`DEFAULT_PIPELINE_DENOISE: expected medium, got ${DEFAULT_PIPELINE_DENOISE}`);
}

if (DEFAULT_PIPELINE_CPL !== "none") {
  throw new Error(`DEFAULT_PIPELINE_CPL: expected none, got ${DEFAULT_PIPELINE_CPL}`);
}

if (DEFAULT_PIPELINE_CHROMA_CLEAN !== "medium") {
  throw new Error(`DEFAULT_PIPELINE_CHROMA_CLEAN: expected medium, got ${DEFAULT_PIPELINE_CHROMA_CLEAN}`);
}

const store = new Map<string, string>();
const fakeStorage = {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, value: string) => store.set(key, value),
};

writeProjectPipelinePreset("project-a", "night_cold", fakeStorage);
const storedPreset = readProjectPipelinePreset("project-a", fakeStorage);
if (storedPreset !== "night_cold") {
  throw new Error(`readProjectPipelinePreset: expected night_cold, got ${storedPreset}`);
}

store.set(pipelinePresetStorageKey("project-b"), "invalid");
if (readProjectPipelinePreset("project-b", fakeStorage) !== null) {
  throw new Error("readProjectPipelinePreset: invalid values should be ignored");
}

if (!isColorGradePreset("outdoor_warm") || isColorGradePreset("bad")) {
  throw new Error("isColorGradePreset: did not validate preset strings correctly");
}

const originalAspectPayload = buildPipelinePayload({
  preset: "night_cold",
  denoise: "medium",
  lensDistort: false,
  levelCorrect: true,
  aspect: "original",
  cplStrength: "medium",
  chromaCleanStrength: "medium",
});
if (
  originalAspectPayload.preset !== "night_cold" ||
  originalAspectPayload.denoise_strength !== "medium" ||
  originalAspectPayload.lens_distort_correct !== false ||
  originalAspectPayload.level_correct !== true ||
  originalAspectPayload.auto_crop_aspect !== null ||
  originalAspectPayload.cpl_strength !== "medium" ||
  originalAspectPayload.chroma_clean_strength !== "medium"
) {
  throw new Error("buildPipelinePayload: did not preserve original-aspect pipeline settings");
}

const croppedPayload = buildPipelinePayload({
  preset: "outdoor_warm",
  denoise: "heavy",
  lensDistort: true,
  levelCorrect: false,
  aspect: "ratio_16_9",
  cplStrength: "high",
  chromaCleanStrength: "high",
});
if (
  croppedPayload.preset !== "outdoor_warm" ||
  croppedPayload.denoise_strength !== "heavy" ||
  croppedPayload.lens_distort_correct !== true ||
  croppedPayload.level_correct !== false ||
  croppedPayload.auto_crop_aspect !== "ratio_16_9" ||
  croppedPayload.cpl_strength !== "high" ||
  croppedPayload.chroma_clean_strength !== "high"
) {
  throw new Error("buildPipelinePayload: did not preserve cropped pipeline settings");
}
