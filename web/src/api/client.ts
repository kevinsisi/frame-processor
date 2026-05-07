import type {
  AutoCropAspect,
  ColorGradePreset,
  Export,
  Photo,
  ProcessingJob,
  Project,
  ProjectDetail,
} from "@/types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json() as Promise<T>;
}

export interface CreateProcessingPayload {
  preset: ColorGradePreset;
  photo_ids?: string[];
  level_correct?: boolean;
  auto_crop_aspect?: AutoCropAspect | string;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),

  getProject: (projectId: string) =>
    request<ProjectDetail>(`/projects/${projectId}`),

  createProject: (name: string) =>
    request<Project>("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),

  uploadPhotos: async (projectId: string, files: File[]): Promise<Photo[]> => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<Photo[]>(`/projects/${projectId}/photos`, {
      method: "POST",
      body: form,
    });
  },

  createExport: (projectId: string) =>
    request<Export>(`/projects/${projectId}/exports`, { method: "POST" }),

  getExport: (exportId: string) => request<Export>(`/exports/${exportId}`),

  exportDownloadUrl: (exportId: string) => `${BASE}/exports/${exportId}/download`,

  photoFileUrl: (photoId: string) => `${BASE}/photos/${photoId}/file`,

  thumbnailUrl: (photoId: string) => `${BASE}/photos/${photoId}/thumbnail`,

  processedPhotoUrl: (photoId: string, preset: ColorGradePreset) =>
    `${BASE}/photos/${photoId}/processed/${preset}`,

  createProcessing: (projectId: string, payload: CreateProcessingPayload) =>
    request<ProcessingJob>(`/projects/${projectId}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        preset: payload.preset,
        photo_ids: payload.photo_ids ?? [],
        level_correct: payload.level_correct ?? true,
        auto_crop_aspect: payload.auto_crop_aspect ?? "original",
      }),
    }),

  getProcessing: (jobId: string) =>
    request<ProcessingJob>(`/processing-jobs/${jobId}`),
};
