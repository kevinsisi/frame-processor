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
};

export type ProjectDetail = Project & {
  photos: Photo[];
};

export type ExportStatus = "pending" | "running" | "done" | "failed";

export type Export = {
  id: string;
  project_id: string;
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

export type ProcessingJobStatus = "pending" | "running" | "done" | "failed";

export type ProcessingJob = {
  id: string;
  project_id: string;
  status: ProcessingJobStatus;
  preset: ColorGradePreset;
  denoise_strength: DenoiseStrength;
  lens_distort_correct: boolean;
  level_correct: boolean;
  auto_crop_aspect: AspectRatio | null;
  photo_ids: string[];
  progress: number;
  total: number;
  error: string | null;
  created_at: string;
  completed_at: string | null;
};

export type ProcessingJobCreate = {
  preset: ColorGradePreset;
  denoise_strength?: DenoiseStrength;
  lens_distort_correct?: boolean;
  level_correct?: boolean;
  auto_crop_aspect?: AspectRatio | null;
  photo_ids?: string[];
};

export type KeyPoolSource = "db" | "env" | "none";

export type KeyPool = {
  count: number;
  source: KeyPoolSource;
  masked_suffixes: string[];
};

export type Settings = {
  gemini_model: string;
  key_manager_url: string;
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
