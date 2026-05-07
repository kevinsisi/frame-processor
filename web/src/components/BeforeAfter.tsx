import { useCallback, useRef, useState } from "react";

import "./BeforeAfter.css";

export interface BeforeAfterProps {
  beforeUrl: string;
  afterUrl: string;
  alt: string;
}

export function BeforeAfter({ beforeUrl, afterUrl, alt }: BeforeAfterProps) {
  const [percent, setPercent] = useState(50);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);

  const updateFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0) return;
    const ratio = ((clientX - rect.left) / rect.width) * 100;
    setPercent(Math.max(0, Math.min(100, ratio)));
  }, []);

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    draggingRef.current = true;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    updateFromClientX(e.clientX);
  }

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!draggingRef.current) return;
    updateFromClientX(e.clientX);
  }

  function onPointerUp(e: React.PointerEvent<HTMLDivElement>) {
    draggingRef.current = false;
    (e.target as Element).releasePointerCapture?.(e.pointerId);
  }

  return (
    <div
      ref={containerRef}
      className="before-after"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <img
        src={beforeUrl}
        alt={`${alt} before`}
        className="before-after__img before-after__img--before"
        draggable={false}
      />
      <div className="before-after__after-wrap" style={{ width: `${percent}%` }}>
        <img
          src={afterUrl}
          alt={`${alt} after`}
          className="before-after__img before-after__img--after"
          draggable={false}
        />
      </div>
      <div className="before-after__divider" style={{ left: `${percent}%` }}>
        <span className="before-after__handle" aria-hidden>
          ↔
        </span>
      </div>
      <span className="before-after__tag before-after__tag--before">原圖</span>
      <span className="before-after__tag before-after__tag--after">處理後</span>
    </div>
  );
}
