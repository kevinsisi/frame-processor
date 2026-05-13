import type {
  ColorGradePreset,
  AdjustmentApplyResult,
  AdjustmentJob,
  AdjustmentParams,
  AdjustmentPreset,
  AdjustmentSource,
  ClearAdjustmentsResult,
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
const SETTINGS_ADMIN_TOKEN = import.meta.env.VITE_SETTINGS_ADMIN_TOKEN ?? "";

export const settingsAdminTokenAvailable = SETTINGS_ADMIN_TOKEN.trim().length > 0;

function resolveSettingsToken(token: string): string {
  return token.trim() || SETTINGS_ADMIN_TOKEN;
}

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

  createExport: (projectId: string, payload?: { processing_job_id?: string | null; allow_partial?: boolean }) =>
    request<Export>(`/projects/${projectId}/exports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload ?? {}),
    }),

  getExport: (exportId: string) => request<Export>(`/exports/${exportId}`),

  exportDownloadUrl: (exportId: string) => `${BASE}/exports/${exportId}/download`,

  photoFileUrl: (photoId: string) => `${BASE}/photos/${photoId}/file`,

  processedPhotoUrl: (photoId: string, preset: ColorGradePreset | "adjusted") =>
    `${BASE}/photos/${photoId}/file?variant=processed&preset=${preset}`,

  adjustmentVersionUrl: (photoId: string, versionId: string) =>
    `${BASE}/photos/${photoId}/file?version_id=${versionId}`,

  processingVersionUrl: (photoId: string, jobId: string) =>
    `${BASE}/photos/${photoId}/file?processing_job_id=${jobId}`,

  createProcessingJob: (projectId: string, payload: ProcessingJobCreate) =>
    request<ProcessingJob>(`/projects/${projectId}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  getProcessingJob: (jobId: string) =>
    request<ProcessingJob>(`/processing-jobs/${jobId}`),

  archiveProcessingVersion: (jobId: string) =>
    request<ProcessingJob>(`/processing-jobs/${jobId}/version`, { method: "DELETE" }),

  getSettings: () => request<Settings>("/settings"),

  updateGeminiKeys: (payload: GeminiKeysUpdate, token: string) =>
    request<GeminiKeysUpdateResult>("/settings/gemini-api-keys", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-Settings-Token": resolveSettingsToken(token),
      },
      body: JSON.stringify(payload),
    }),

  clearGeminiKeys: (token: string) =>
    fetch(`${BASE}/settings/gemini-api-keys`, {
      method: "DELETE",
      headers: { "X-Settings-Token": resolveSettingsToken(token) },
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
      headers: {
        "Content-Type": "application/json",
        "X-Settings-Token": resolveSettingsToken(token),
      },
      body: JSON.stringify(payload),
    }),

  previewAdjustment: async (photoId: string, payload: AdjustmentParams) => {
    const response = await fetch(`${BASE}/photos/${photoId}/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${text}`);
    }
    return response.blob();
  },

  applyAdjustment: (photoId: string, payload: AdjustmentParams) =>
    request<AdjustmentApplyResult>(`/photos/${photoId}/adjustments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  saveAdjustmentDraft: (photoId: string, payload: AdjustmentParams) =>
    request<AdjustmentApplyResult>(`/photos/${photoId}/adjustments/draft`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  createAdjustmentJob: (
    projectId: string,
    payload: AdjustmentParams,
    photoIds: string[],
    sources?: Record<string, AdjustmentSource>,
  ) =>
    request<AdjustmentJob>(`/projects/${projectId}/adjustments/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ params: payload, photo_ids: photoIds, sources: sources ?? {} }),
    }),

  clearPhotoAdjustments: (projectId: string, photoIds: string[]) =>
    request<ClearAdjustmentsResult>(`/projects/${projectId}/adjustments/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ photo_ids: photoIds }),
    }),

  getAdjustmentJob: (jobId: string) =>
    request<AdjustmentJob>(`/adjustment-jobs/${jobId}`),

  listAdjustmentPresets: (projectId?: string) =>
    request<AdjustmentPreset[]>(
      `/adjustment-presets${projectId ? `?project_id=${projectId}` : ""}`,
    ),

  createAdjustmentPreset: (name: string, params: AdjustmentParams, projectId?: string) =>
    request<AdjustmentPreset>("/adjustment-presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, params, project_id: projectId ?? null }),
    }),

  deleteAdjustmentPreset: (presetId: string) =>
    fetch(`${BASE}/adjustment-presets/${presetId}`, { method: "DELETE" }).then(
      (response) => {
        if (!response.ok) {
          return response.text().then((text) => {
            throw new Error(`${response.status} ${response.statusText}: ${text}`);
          });
        }
      },
    ),
};
