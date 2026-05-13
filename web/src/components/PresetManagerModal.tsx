import { useEffect } from "react";

import type { AdjustmentPreset } from "@/types";

import "./PresetManagerModal.css";

type Props = {
  presets: AdjustmentPreset[];
  busy: boolean;
  onClose: () => void;
  onDeletePreset: (preset: AdjustmentPreset) => void;
};

export function PresetManagerModal({ presets, busy, onClose, onDeletePreset }: Props) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  function handleDelete(preset: AdjustmentPreset) {
    if (busy) return;
    const ok = window.confirm(
      `刪除 preset「${preset.name}」？\n\n（只移除這個 template，照片上的微調不會變動，無法復原。）`,
    );
    if (ok) onDeletePreset(preset);
  }

  return (
    <div
      className="preset-modal__overlay"
      role="dialog"
      aria-modal="true"
      aria-label="管理 preset"
      onClick={onClose}
    >
      <div
        className="preset-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="preset-modal__head">
          <h3 className="preset-modal__title">管理 Presets</h3>
          <button
            type="button"
            className="preset-modal__close"
            onClick={onClose}
            aria-label="關閉"
          >
            ✕
          </button>
        </header>

        <p className="preset-modal__disclaimer">
          <strong>刪除 preset 只移除 template，不會動到任何照片。</strong>
          要清空照片上的微調請用主面板的「清空目前照片的微調」或「清空已選 N 張的微調」。
        </p>

        {presets.length === 0 ? (
          <p className="preset-modal__empty">尚未儲存任何 preset。</p>
        ) : (
          <ul className="preset-modal__list">
            {presets.map((preset) => (
              <li key={preset.id} className="preset-modal__row">
                <span className="preset-modal__name">{preset.name}</span>
                <button
                  type="button"
                  className="cta cta--quiet preset-modal__delete"
                  onClick={() => handleDelete(preset)}
                  disabled={busy}
                >
                  刪除
                </button>
              </li>
            ))}
          </ul>
        )}

        <footer className="preset-modal__foot">
          <button type="button" className="cta" onClick={onClose}>
            完成
          </button>
        </footer>
      </div>
    </div>
  );
}
