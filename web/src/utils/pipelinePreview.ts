export function needsPipelineRunNote({
  sourceKind,
  processedPaths,
  pipelinePreset,
  hasActivePreview,
}: {
  sourceKind: string | null | undefined;
  processedPaths: Record<string, string> | null | undefined;
  pipelinePreset: string;
  hasActivePreview: boolean;
}): boolean {
  return Boolean(
    hasActivePreview &&
      sourceKind === "original" &&
      !(processedPaths ?? {})[pipelinePreset],
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
