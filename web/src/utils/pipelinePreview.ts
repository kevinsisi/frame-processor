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
