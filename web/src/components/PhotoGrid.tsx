import { api } from "@/api/client";
import type { Photo } from "@/types";

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
  onToggleSelect?: (photoId: string) => void;
}

export function PhotoGrid({
  photos,
  selectable = false,
  selectedIds,
  onToggleSelect,
}: PhotoGridProps) {
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
        const Tag: "li" = "li";
        const handleClick = () => {
          if (selectable && onToggleSelect) onToggleSelect(photo.id);
        };
        return (
          <Tag
            key={photo.id}
            className={`photo-tile${selected ? " photo-tile--selected" : ""}${
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
                <span className="photo-tile__check" aria-hidden>
                  ✓
                </span>
              )}
            </div>
            <a
              href={api.photoFileUrl(photo.id)}
              target="_blank"
              rel="noreferrer"
              className="photo-tile__open mono"
              onClick={(e) => e.stopPropagation()}
            >
              開原檔 ↗
            </a>
          </Tag>
        );
      })}
    </ul>
  );
}
