import { missingPipelineOutputPhotoIds, needsPipelineRunNote } from "../src/utils/pipelinePreview.js";

function assertEqual(actual: boolean, expected: boolean, label: string): void {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

assertEqual(
  needsPipelineRunNote({
    sourceKind: "original",
    processedPaths: {},
    pipelinePreset: "showroom_white",
    hasActivePreview: true,
  }),
  true,
  "original without output shows note",
);

assertEqual(
  needsPipelineRunNote({
    sourceKind: "original",
    processedPaths: { showroom_white: "processed.jpg" },
    pipelinePreset: "showroom_white",
    hasActivePreview: true,
  }),
  false,
  "existing pipeline output hides note",
);

assertEqual(
  needsPipelineRunNote({
    sourceKind: "preset",
    processedPaths: {},
    pipelinePreset: "showroom_white",
    hasActivePreview: true,
  }),
  false,
  "non-original source hides note",
);

assertEqual(
  needsPipelineRunNote({
    sourceKind: "original",
    processedPaths: {},
    pipelinePreset: "showroom_white",
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
