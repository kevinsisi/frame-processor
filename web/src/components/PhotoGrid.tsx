import { api } from "@/api/client";
import type { Photo } from "@/types";

export function PhotoGrid({ photos }: { photos: Photo[] }) {
  if (photos.length === 0) {
    return <div className="text-sm text-slate-500">尚無照片。</div>;
  }
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {photos.map((photo) => (
        <a
          key={photo.id}
          href={api.photoFileUrl(photo.id)}
          target="_blank"
          rel="noreferrer"
          className="block rounded-md overflow-hidden border border-slate-200 bg-slate-100 group"
        >
          <div className="aspect-[4/3] bg-slate-200">
            <img
              src={api.photoFileUrl(photo.id)}
              alt={photo.original_filename}
              loading="lazy"
              className="w-full h-full object-cover group-hover:opacity-90 transition-opacity"
            />
          </div>
          <div className="px-2 py-1 text-xs text-slate-600 truncate" title={photo.original_filename}>
            {photo.original_filename}
          </div>
        </a>
      ))}
    </div>
  );
}
