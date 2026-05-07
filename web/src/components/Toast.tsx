import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import "./Toast.css";

type ToastTone = "info" | "success" | "error";

interface ToastEntry {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  push: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);
  const idRef = useRef(0);

  const push = useCallback((message: string, tone: ToastTone = "info") => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { id, message, tone }]);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <ToastItem
            key={t.id}
            entry={t}
            onDone={() =>
              setToasts((prev) => prev.filter((x) => x.id !== t.id))
            }
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ entry, onDone }: { entry: ToastEntry; onDone: () => void }) {
  useEffect(() => {
    const timer = window.setTimeout(onDone, 4200);
    return () => window.clearTimeout(timer);
  }, [onDone]);
  return <div className={`toast toast--${entry.tone}`}>{entry.message}</div>;
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return ctx;
}
