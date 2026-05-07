import { useCallback, useRef, useState } from "react";
import type { DragEvent } from "react";

import "./Dropzone.css";

export interface DropzoneProps {
  onPick: (files: File[]) => void;
  accept?: string;
  hint?: string;
  ctaLabel?: string;
  disabled?: boolean;
}

export function Dropzone({
  onPick,
  accept = "image/*",
  hint = "把照片拖進這裡，或點下方按鈕從電腦選取。可一次選多張。",
  ctaLabel = "選取照片 +",
  disabled = false,
}: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [hover, setHover] = useState(false);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setHover(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files).filter((f) =>
        f.type.startsWith("image/"),
      );
      if (files.length > 0) onPick(files);
    },
    [onPick, disabled],
  );

  const handleDragOver = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!disabled) setHover(true);
    },
    [disabled],
  );

  return (
    <div
      className={`dropzone${hover ? " dropzone--hover" : ""}${
        disabled ? " dropzone--disabled" : ""
      }`}
      onDragOver={handleDragOver}
      onDragLeave={() => setHover(false)}
      onDrop={handleDrop}
    >
      <div className="dropzone__icon" aria-hidden>
        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect
            x="6"
            y="10"
            width="36"
            height="28"
            stroke="currentColor"
            strokeWidth="1.2"
          />
          <path
            d="M6 32 L18 22 L26 28 L34 20 L42 28"
            stroke="currentColor"
            strokeWidth="1.2"
            fill="none"
          />
          <circle cx="32" cy="18" r="2.4" stroke="currentColor" strokeWidth="1.2" />
        </svg>
      </div>
      <p className="dropzone__hint">{hint}</p>
      <p className="dropzone__hint dropzone__hint--meta">
        支援 JPG / PNG / HEIC。原圖不會被覆寫，處理結果會另存。
      </p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        className="dropzone__input"
        disabled={disabled}
        onChange={(e) => {
          if (e.target.files) {
            onPick(Array.from(e.target.files));
            e.target.value = "";
          }
        }}
      />
      <button
        type="button"
        className="dropzone__btn"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        {ctaLabel}
      </button>
    </div>
  );
}
