import type {
  ColorGradePreset,
  Export,
  Photo,
  ProcessingJob,
  ProcessingJobCreate,
  Project,
  ProjectDetail,
  GeminiKeysUpdate,
  GeminiKeysUpdateResult,
  Settings,
  SyncFromKeyManager,
  SyncFromKeyManagerResult,
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

  processedPhotoUrl: (photoId: string, preset: ColorGradePreset) =>
    `${BASE}/photos/${photoId}/file?variant=processed&preset=${preset}`,

  createProcessingJob: (projectId: string, payload: ProcessingJobCreate) =>
    request<ProcessingJob>(`/projects/${projectId}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  getProcessingJob: (jobId: string) =>
    request<ProcessingJob>(`/processing-jobs/${jobId}`),

  getSettings: () => request<Settings>("/settings"),

  updateGeminiKeys: (payload: GeminiKeysUpdate, token: string) =>
    request<GeminiKeysUpdateResult>("/settings/gemini-api-keys", {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Settings-Token": token },
      body: JSON.stringify(payload),
    }),

  clearGeminiKeys: (token: string) =>
    fetch(`${BASE}/settings/gemini-api-keys`, {
      method: "DELETE",
      headers: { "X-Settings-Token": token },
    }).then(
      (response) => {
        if (!response.ok) {
          return response.text().then((text) => {
            throw new Error(`${response.status} ${response.statusText}: ${text}`);
          });
        }
      },
    ),

  syncKeysFromManager: (payload: SyncFromKeyManager, token: string) =>
    request<SyncFromKeyManagerResult>("/settings/sync-from-key-manager", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Settings-Token": token },
      body: JSON.stringify(payload),
    }),
};
