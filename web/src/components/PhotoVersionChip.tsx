import type { Photo, ProcessingVersion } from "@/types";
import { formatAIVersionLabel, formatAIVersionFallbackLabel } from "@/utils/processingVersionLabel";

import "./PhotoVersionChip.css";

type Props = {
  photo: Photo;
  processingVersions: ProcessingVersion[];
};

type ChipState =
  | { kind: "none" }
  | { kind: "ai"; label: string }
  | { kind: "manual"; label: string };

export function PhotoVersionChip({ photo, processingVersions }: Props) {
  const latestAi = pickLatestAiChip(photo, processingVersions);
  const latestManual = pickLatestManualChip(photo);
  const totalVersions = countVersions(photo);
  const fullyEmpty = latestAi.kind === "none" && latestManual.kind === "none";

  if (fullyEmpty) {
    return (
      <div className="photo-version-chips">
        <span className="photo-version-chip photo-version-chip--original">原圖</span>
        <span className="photo-version-chip photo-version-chip--muted">尚未處理</span>
      </div>
    );
  }

  return (
    <div className="photo-version-chips">
      {latestAi.kind === "ai" ? (
        <span className="photo-version-chip photo-version-chip--ai" title={latestAi.label}>
          {latestAi.label}
        </span>
      ) : (
        <span className="photo-version-chip photo-version-chip--muted">無 AI 版本</span>
      )}
      {latestManual.kind === "manual" ? (
        <span className="photo-version-chip photo-version-chip--manual" title={latestManual.label}>
          {latestManual.label}
        </span>
      ) : (
        <span className="photo-version-chip photo-version-chip--muted">無手動</span>
      )}
      {totalVersions > 0 && (
        <span className="photo-version-chip__count mono">▼ {totalVersions} 個版本</span>
      )}
    </div>
  );
}

function pickLatestAiChip(photo: Photo, processingVersions: ProcessingVersion[]): ChipState {
  const doneVersions = (photo.processing_versions ?? []).filter(
    (v) => v.status === "done" && Boolean(v.path),
  );
  if (doneVersions.length === 0) return { kind: "none" };
  const latest = doneVersions.reduce((prev, curr) => {
    const prevTime = prev.created_at ? Date.parse(prev.created_at) : 0;
    const currTime = curr.created_at ? Date.parse(curr.created_at) : 0;
    return currTime > prevTime ? curr : prev;
  });
  const job = processingVersions.find((item) => item.id === latest.processing_job_id);
  const label = job ? formatAIVersionLabel(job) : formatAIVersionFallbackLabel(latest.version_number);
  return { kind: "ai", label };
}

function pickLatestManualChip(photo: Photo): ChipState {
  const versions = photo.adjustment_versions ?? [];
  if (versions.length === 0) return { kind: "none" };
  const latest = versions.reduce((prev, curr) =>
    curr.version_number > prev.version_number ? curr : prev,
  );
  return { kind: "manual", label: `手動 v${latest.version_number}` };
}

function countVersions(photo: Photo): number {
  const aiCount = (photo.processing_versions ?? []).filter(
    (v) => v.status === "done" && Boolean(v.path),
  ).length;
  const manualCount = (photo.adjustment_versions ?? []).length;
  const presetCount = Object.keys(photo.processed_paths ?? {}).filter(
    (key) => key !== "adjusted",
  ).length;
  return aiCount + manualCount + presetCount;
}
