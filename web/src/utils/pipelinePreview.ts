export function needsPipelineRunNote({
  sourceKind,
  hasMatchingPipelineOutput,
  hasActivePreview,
}: {
  sourceKind: string | null | undefined;
  hasMatchingPipelineOutput: boolean;
  hasActivePreview: boolean;
}): boolean {
  return Boolean(
    hasActivePreview &&
      sourceKind === "original" &&
      !hasMatchingPipelineOutput,
  );
}

export function missingPipelineOutputPhotoIds(
  photos: Array<{ id: string; processed_paths?: Record<string, string> | null }>,
  pipelinePreset: string,
): string[] {
  return photos
    .filter((photo) => !(photo.processed_paths ?? {})[pipelinePreset])
    .map((photo) => photo.id);
}

export function automaticPipelineCandidatePhotoIds(
  photos: Array<{
    id: string;
    processed_paths?: Record<string, string> | null;
    processing_versions?: Array<{ status: string; path?: string | null }> | null;
  }>,
): string[] {
  return photos
    .filter((photo) => {
      const hasLegacyPipelineOutput = Object.entries(photo.processed_paths ?? {}).some(
        ([key, path]) => key !== "adjusted" && Boolean(path),
      );
      if (hasLegacyPipelineOutput) return false;
      return !(photo.processing_versions ?? []).some((version) => version.status === "done" && version.path);
    })
    .map((photo) => photo.id);
}
