import { useState } from "react";

import { api } from "@/api/client";
import type { ColorGradePreset, Photo } from "@/types";

import "./PhotoGrid.css";

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
  onToggleSelect?: (photoId: string) => void;
  onOpenPreview?: (photoId: string) => void;
}

export function PhotoGrid({
  photos,
  selectable = false,
  selectedIds,
  activeId,
  onToggleSelect,
  onOpenPreview,
}: PhotoGridProps) {
  const [downloadVersions, setDownloadVersions] = useState<Record<string, string>>({});
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
        const processedPresets = Object.keys(photo.processed_paths ?? {});
        const versionOptions = buildVersionOptions(photo, processedPresets);
        const selectedDownloadVersion = downloadVersions[photo.id] ?? versionOptions[0].value;
        const selectedOption =
          versionOptions.find((option) => option.value === selectedDownloadVersion) ??
          versionOptions[0];
        const Tag: "li" = "li";
        const handleClick = () => {
          onOpenPreview?.(photo.id);
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
                src={api.photoFileUrl(photo.id)}
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
            </div>
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
                  event.stopPropagation();
                  setDownloadVersions((prev) => ({
                    ...prev,
                    [photo.id]: event.target.value,
                  }));
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
                className="photo-tile__open mono"
                onClick={(e) => e.stopPropagation()}
              >
                下載版本 ↓
              </a>
            </div>
          </Tag>
        );
      })}
    </ul>
  );
}

function buildVersionOptions(photo: Photo, processedPresets: string[]) {
  const options: { value: string; label: string; url: string }[] = [];
  for (const version of photo.adjustment_versions ?? []) {
    options.push({
      value: `manual:${version.id}`,
      label: `手動 v${version.version_number}`,
      url: api.adjustmentVersionUrl(photo.id, version.id),
    });
  }
  for (const preset of processedPresets) {
    if (preset === "adjusted") continue;
    options.push({
      value: `preset:${preset}`,
      label: presetLabel(preset),
      url: api.processedPhotoUrl(photo.id, preset as ColorGradePreset),
    });
  }
  if ((photo.processed_paths ?? {}).adjusted && (photo.adjustment_versions ?? []).length === 0) {
    options.push({
      value: "preset:adjusted",
      label: "手動 latest",
      url: api.processedPhotoUrl(photo.id, "adjusted"),
    });
  }
  options.push({
    value: "original",
    label: "原圖",
    url: api.photoFileUrl(photo.id),
  });
  return options;
}

function presetLabel(preset: string): string {
  if (preset === "showroom_white") return "展間白";
  if (preset === "outdoor_warm") return "戶外暖";
  if (preset === "night_cold") return "夜拍冷";
  return preset;
}
