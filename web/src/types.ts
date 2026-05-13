export type Project = {
  id: string;
  name: string;
  created_at: string;
  photo_count: number;
};

export type Photo = {
  id: string;
  project_id: string;
  original_filename: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  mime_type: string | null;
  uploaded_at: string;
  processed_paths: Record<string, string>;
  adjustment_params: AdjustmentParams | null;
  adjustment_versions: AdjustmentVersion[];
  processing_versions: ProcessingVersionPhoto[];
};

export type AdjustmentVersion = {
  id: string;
  photo_id: string;
  version_number: number;
  params: AdjustmentParams;
  path: string;
  created_at: string;
};

export type ProjectDetail = Project & {
  photos: Photo[];
  processing_versions: ProcessingVersion[];
};

export type ExportStatus = "pending" | "running" | "done" | "failed";

export type Export = {
  id: string;
  project_id: string;
  processing_job_id: string | null;
  allow_partial: boolean;
  status: ExportStatus;
  error: string | null;
  created_at: string;
  completed_at: string | null;
};

export type ColorGradePreset = "showroom_white" | "outdoor_warm" | "night_cold";

export type AspectRatio =
  | "original"
  | "ratio_3_2"
  | "ratio_4_3"
  | "ratio_16_9"
  | "ratio_1_1"
  | "ratio_9_16";

export type DenoiseStrength = "none" | "light" | "medium" | "heavy";

export type CplStrength = "none" | "low" | "medium" | "high";

export type ChromaCleanStrength = "none" | "low" | "medium" | "high";

export type DetailPreserveStrength = "none" | "low" | "medium" | "high";

export type ProcessingJobStatus = "pending" | "running" | "done" | "failed";

export type ProcessingRetryScope = "none" | "full" | "missing_only";

export type ProcessingJob = {
  id: string;
  project_id: string;
  status: ProcessingJobStatus;
  version_number: number;
  preset: ColorGradePreset;
  denoise_strength: DenoiseStrength;
  lens_distort_correct: boolean;
  level_correct: boolean;
  auto_crop_aspect: AspectRatio | null;
  cpl_strength: CplStrength;
  chroma_clean_strength: ChromaCleanStrength;
  detail_preserve_strength: DetailPreserveStrength;
  photo_ids: string[];
  progress: number;
  total: number;
  error: string | null;
  retry_scope: ProcessingRetryScope;
  retry_of_job_id: string | null;
  created_at: string;
  completed_at: string | null;
};

export type ProcessingVersion = ProcessingJob;

export type ProcessingVersionPhoto = {
  processing_job_id: string;
  version_number: number;
  status: "done" | "failed" | string;
  path: string | null;
  error: string | null;
  created_at: string;
};

export type ProcessingJobCreate = {
  preset: ColorGradePreset;
  denoise_strength?: DenoiseStrength;
  lens_distort_correct?: boolean;
  level_correct?: boolean;
  auto_crop_aspect?: AspectRatio | null;
  cpl_strength?: CplStrength;
  chroma_clean_strength?: ChromaCleanStrength;
  detail_preserve_strength?: DetailPreserveStrength;
  photo_ids?: string[];
  force?: boolean;
  retry_scope?: ProcessingRetryScope;
  retry_of_job_id?: string | null;
};

export type KeyPoolSource = "db" | "env" | "none";

export type KeyPool = {
  count: number;
  source: KeyPoolSource;
  masked_suffixes: string[];
};

export type Settings = {
  gemini_model: string;
  key_manager_url: string | null;
  settings_admin_configured: boolean;
  gemini_api_keys: KeyPool;
};

export type GeminiKeysUpdate = {
  raw: string;
  replace: boolean;
};

export type GeminiKeysUpdateResult = {
  stored_count: number;
  accepted_count: number;
  rejected_count: number;
};

export type SyncFromKeyManager = {
  trusted_only: boolean;
  replace: boolean;
};

export type SyncFromKeyManagerResult = {
  fetched: number;
  imported: number;
  skipped: number;
  stored_count: number;
};

export type HslColor = "red" | "orange" | "yellow" | "green" | "blue" | "purple";

export type HslAdjustment = {
  hue: number;
  saturation: number;
  luminance: number;
};

export type AdjustmentParams = {
  exposure: number;
  contrast: number;
  highlights: number;
  shadows: number;
  temperature: number;
  tint: number;
  saturation: number;
  vibrance: number;
  clarity: number;
  sharpness: number;
  orientation: number;
  rotation: number;
  crop_zoom: number;
  crop_x: number;
  crop_y: number;
  distortion: number;
  distortion_x: number;
  distortion_y: number;
  hsl: Record<HslColor, HslAdjustment>;
  source?: AdjustmentSource | null;
  grade_preset?: ColorGradePreset | null;
};

export type AdjustmentSource = {
  kind: "auto" | "original" | "preset" | "manual" | "processing";
  value?: string | null;
};

export type AdjustmentApplyResult = {
  photo_id: string;
  processed_path: string;
  params: AdjustmentParams;
};

export type ClearAdjustmentsResult = {
  cleared_count: number;
  photos: Photo[];
};

export type AdjustmentJob = {
  id: string;
  project_id: string;
  status: ProcessingJobStatus;
  params: AdjustmentParams;
  photo_ids: string[];
  progress: number;
  total: number;
  error: string | null;
  created_at: string;
  completed_at: string | null;
};

export type AdjustmentPreset = {
  id: string;
  project_id: string | null;
  name: string;
  params: AdjustmentParams;
  created_at: string;
};
