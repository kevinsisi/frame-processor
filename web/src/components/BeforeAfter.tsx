import { useCallback, useEffect, useRef, useState } from "react";

import "./BeforeAfter.css";

export interface BeforeAfterProps {
  beforeUrl: string;
  afterUrl: string;
  beforeLabel?: string;
  afterLabel?: string;
  alt: string;
}

/**
 * 編輯感對比拖拉條：左側 before、右側 after，中間黃金分隔線可拖。
 * 純 CSS clip-path（after 圖片做 inset），不引第三方套件。
 */
export function BeforeAfter({
  beforeUrl,
  afterUrl,
  beforeLabel = "原圖",
  afterLabel = "處理後",
  alt,
}: BeforeAfterProps) {
  const [position, setPosition] = useState(50); // 0~100
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const setFromClientX = useCallback((clientX: number) => {
    const node = containerRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const ratio = ((clientX - rect.left) / rect.width) * 100;
    setPosition(Math.max(0, Math.min(100, ratio)));
  }, []);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (event: PointerEvent) => setFromClientX(event.clientX);
    const onUp = () => setDragging(false);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [dragging, setFromClientX]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setPosition((p) => Math.max(0, p - 4));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setPosition((p) => Math.min(100, p + 4));
    } else if (event.key === "Home") {
      setPosition(0);
    } else if (event.key === "End") {
      setPosition(100);
    }
  }

  return (
    <div
      className="before-after"
      ref={containerRef}
      onPointerDown={(e) => {
        setDragging(true);
        setFromClientX(e.clientX);
      }}
    >
      <img className="before-after__img" src={beforeUrl} alt={`${alt} · ${beforeLabel}`} />
      <img
        className="before-after__img before-after__img--after"
        src={afterUrl}
        alt={`${alt} · ${afterLabel}`}
        style={{ clipPath: `inset(0 0 0 ${position}%)` }}
      />
      <span className="before-after__tag before-after__tag--left mono" aria-hidden>
        {beforeLabel}
      </span>
      <span className="before-after__tag before-after__tag--right mono" aria-hidden>
        {afterLabel}
      </span>
      <div
        role="slider"
        tabIndex={0}
        aria-label="對比拖拉"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(position)}
        onKeyDown={handleKeyDown}
        className="before-after__handle"
        style={{ left: `${position}%` }}
      >
        <span className="before-after__handle-bar" aria-hidden />
        <span className="before-after__handle-grip" aria-hidden>
          ⇿
        </span>
      </div>
    </div>
  );
}
