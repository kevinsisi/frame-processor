export type Project = {
  id: string;
  name: string;
  created_at: string;
  photo_count: number;
};

export type ColorGradePreset = "showroom_white" | "outdoor_warm" | "night_cold";

export type Photo = {
  id: string;
  project_id: string;
  original_filename: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  mime_type: string | null;
  uploaded_at: string;
  processed_paths: Partial<Record<ColorGradePreset, string>>;
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

export type ProcessingJobStatus = "pending" | "running" | "done" | "failed";

export type AutoCropAspect =
  | "original"
  | "3:2"
  | "4:3"
  | "16:9"
  | "1:1"
  | "9:16";

export type ProcessingJob = {
  id: string;
  project_id: string;
  preset: ColorGradePreset;
  level_correct: boolean;
  auto_crop_aspect: AutoCropAspect | string;
  status: ProcessingJobStatus;
  progress_done: number;
  progress_total: number;
  error: string | null;
  created_at: string;
  completed_at: string | null;
};
