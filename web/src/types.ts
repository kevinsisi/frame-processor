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
