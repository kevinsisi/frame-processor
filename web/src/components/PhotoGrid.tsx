import { useState } from "react";

import { api } from "@/api/client";
import { PhotoVersionChip } from "@/components/PhotoVersionChip";
import type { AdjustmentSource, ColorGradePreset, Photo, ProcessingVersion } from "@/types";
import {
  formatAIVersionFallbackLabel,
  formatAIVersionLabel,
  formatBatchPresetLabel,
} from "@/utils/processingVersionLabel";

import "./PhotoGrid.css";

const DOWNLOADED_PHOTO_VERSIONS_KEY = "frame-processor:downloaded-photo-versions:v1";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export interface PhotoGridProps {
  photos: Photo[];
  selectable?: boolean;
  selectedIds?: Set<string>;
  activeId?: string | null;
  versionValues?: Record<string, string>;
  processingVersions?: ProcessingVersion[];
  onToggleSelect?: (photoId: string) => void;
  onOpenPreview?: (photoId: string) => void;
  onVersionChange?: (photoId: string, value: string, option: PhotoVersionOption) => void;
}

export type PhotoVersionOption = {
  value: string;
  label: string;
  url: string;
  source: AdjustmentSource;
};

export function PhotoGrid({
  photos,
  selectable = false,
  selectedIds,
  activeId,
  versionValues,
  processingVersions = [],
  onToggleSelect,
  onOpenPreview,
  onVersionChange,
}: PhotoGridProps) {
  const [internalVersions, setInternalVersions] = useState<Record<string, string>>({});
  const [downloadedVersions, setDownloadedVersions] = useState<Set<string>>(() => loadDownloadedPhotoVersions());
  if (photos.length === 0) {
    return (
      <div className="photo-grid__empty">
        <span className="mono">尚無照片</span>
      </div>
    );
  }
  return (
    <ul className="photo-grid">
      {photos.map((photo) => {
        const selected = selectedIds?.has(photo.id) ?? false;
        const active = activeId === photo.id;
        const versionOptions = buildPhotoVersionOptions(photo, processingVersions);
        const selectedDownloadVersion =
          versionValues?.[photo.id] ?? internalVersions[photo.id] ?? defaultPhotoVersionOption(versionOptions).value;
        const selectedOption =
          versionOptions.find((option) => option.value === selectedDownloadVersion) ??
          versionOptions[0];
        const selectedDownloadKey = downloadedPhotoVersionKey(photo.id, selectedOption.value);
        const selectedVersionDownloaded = downloadedVersions.has(selectedDownloadKey);
        const photoDownloaded = versionOptions.some((option) => downloadedVersions.has(downloadedPhotoVersionKey(photo.id, option.value)));
        const Tag: "li" = "li";
        const handleClick = () => {
          onOpenPreview?.(photo.id);
        };
        const markDownloaded = () => {
          setDownloadedVersions((prev) => {
            const next = new Set(prev);
            next.add(selectedDownloadKey);
            saveDownloadedPhotoVersions(next);
            return next;
          });
        };
        return (
          <Tag
            key={photo.id}
            className={`photo-tile${selected ? " photo-tile--selected" : ""}${
              active ? " photo-tile--active" : ""
            }${
              selectable ? " photo-tile--selectable" : ""
            }`}
            onClick={handleClick}
          >
            <div className="photo-tile__frame">
              <img
                src={selectedOption.url}
                alt={photo.original_filename}
                loading="lazy"
                className="photo-tile__img"
              />
              <div className="photo-tile__overlay">
                <span className="photo-tile__name" title={photo.original_filename}>
                  {photo.original_filename}
                </span>
                <span className="photo-tile__meta mono">
                  {photo.width && photo.height
                    ? `${photo.width}×${photo.height} · `
                    : ""}
                  {formatBytes(photo.size_bytes)}
                </span>
              </div>
              {selectable && (
                <button
                  type="button"
                  className="photo-tile__check"
                  aria-label={selected ? "取消選取" : "選取照片"}
                  onClick={(event) => {
                    event.stopPropagation();
                    onToggleSelect?.(photo.id);
                  }}
                >
                  ✓
                </button>
              )}
              {photoDownloaded && <span className="photo-tile__downloaded-badge mono">已下載</span>}
            </div>
            <PhotoVersionChip photo={photo} processingVersions={processingVersions} />
            <div className="photo-tile__actions">
              <a
                href={api.photoFileUrl(photo.id)}
                target="_blank"
                rel="noreferrer"
                className="photo-tile__open mono"
                onClick={(e) => e.stopPropagation()}
              >
                開原檔 ↗
              </a>
              <select
                className="photo-tile__version mono"
                value={selectedOption.value}
                onClick={(e) => e.stopPropagation()}
                onChange={(event) => {
                  const option =
                    versionOptions.find((item) => item.value === event.target.value) ??
                    versionOptions[0];
                  event.stopPropagation();
                  setInternalVersions((prev) => ({
                    ...prev,
                    [photo.id]: event.target.value,
                  }));
                  onVersionChange?.(photo.id, event.target.value, option);
                }}
              >
                {versionOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <a
                href={selectedOption.url}
                download
                className={`photo-tile__open mono${selectedVersionDownloaded ? " photo-tile__open--downloaded" : ""}`}
                onClick={(e) => {
                  e.stopPropagation();
                  markDownloaded();
                }}
              >
                {selectedVersionDownloaded ? "此版本已下載 ✓" : "下載版本 ↓"}
              </a>
            </div>
          </Tag>
        );
      })}
    </ul>
  );
}

function downloadedPhotoVersionKey(photoId: string, versionValue: string): string {
  return `${photoId}:${versionValue}`;
}

function loadDownloadedPhotoVersions(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(DOWNLOADED_PHOTO_VERSIONS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((item): item is string => typeof item === "string"));
  } catch {
    return new Set();
  }
}

function saveDownloadedPhotoVersions(downloadedVersions: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(DOWNLOADED_PHOTO_VERSIONS_KEY, JSON.stringify([...downloadedVersions]));
  } catch {
    // Some private/restricted browsers block localStorage; keep in-memory markers for this session.
  }
}

export function buildPhotoVersionOptions(
  photo: Photo,
  processingVersions: ProcessingVersion[] = [],
): PhotoVersionOption[] {
  const options: PhotoVersionOption[] = [];
  for (const version of photo.adjustment_versions ?? []) {
    options.push({
      value: `manual:${version.id}`,
      label: `手動版本 v${version.version_number}`,
      url: api.adjustmentVersionUrl(photo.id, version.id),
      source: { kind: "manual", value: version.id },
    });
  }
  for (const version of photo.processing_versions ?? []) {
    if (version.status !== "done" || !version.path) continue;
    const job = processingVersions.find((item) => item.id === version.processing_job_id);
    options.push({
      value: `processing:${version.processing_job_id}`,
      label: job ? formatAIVersionLabel(job) : formatAIVersionFallbackLabel(version.version_number),
      url: api.processingVersionUrl(photo.id, version.processing_job_id),
      source: { kind: "processing", value: version.processing_job_id },
    });
  }
  for (const preset of Object.keys(photo.processed_paths ?? {})) {
    if (preset === "adjusted") continue;
    options.push({
      value: `preset:${preset}`,
      label: formatBatchPresetLabel(preset),
      url: api.processedPhotoUrl(photo.id, preset as ColorGradePreset),
      source: { kind: "preset", value: preset },
    });
  }
  options.push({
    value: "original",
    label: "原圖",
    url: api.photoFileUrl(photo.id),
    source: { kind: "original", value: null },
  });
  return options;
}

export function defaultPhotoVersionOption(options: PhotoVersionOption[]): PhotoVersionOption {
  return options.find((option) => option.value === "original") ?? options[0];
}

