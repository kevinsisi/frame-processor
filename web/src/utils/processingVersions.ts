import type { ProcessingVersion, ProjectDetail } from "../types";

export function photoHasDoneProcessingVersion(
  photo: ProjectDetail["photos"][number],
  versionId: string,
): boolean {
  return Boolean(
    photo.processing_versions?.some(
      (version) => version.processing_job_id === versionId && version.status === "done" && version.path,
    ),
  );
}

export function photoProcessingVersionStatus(
  photo: ProjectDetail["photos"][number],
  versionId: string,
): string | null {
  return photo.processing_versions?.find((version) => version.processing_job_id === versionId)?.status ?? null;
}

export function missingPhotoIdsForProcessingVersion(
  project: ProjectDetail,
  version: ProcessingVersion,
): string[] {
  return version.photo_ids.filter((photoId) => {
    const photo = project.photos.find((item) => item.id === photoId);
    return !photo || !photoHasDoneProcessingVersion(photo, version.id);
  });
}

export function incompletePhotoIdsForProcessingVersion(
  project: ProjectDetail,
  version: ProcessingVersion,
): string[] {
  return version.photo_ids.filter((photoId) => {
    const photo = project.photos.find((item) => item.id === photoId);
    if (!photo) return true;
    return photoProcessingVersionStatus(photo, version.id) !== "done";
  });
}

export function visibleMissingPhotoIdsForProcessingVersion(
  project: ProjectDetail,
  version: ProcessingVersion,
): string[] {
  if (version.status === "pending" || version.status === "running") return [];
  return missingPhotoIdsForProcessingVersion(project, version);
}
