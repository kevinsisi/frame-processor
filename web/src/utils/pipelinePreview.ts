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
