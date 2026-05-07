import "./StylePicker.css";

import type { AutoCropAspect } from "@/types";

// Mirrors models/enums.py:ColorGradePreset.
export type StylePreset = "showroom_white" | "outdoor_warm" | "night_cold";

interface PresetMeta {
  value: StylePreset;
  label: string;
  caption: string;
  description: string;
  swatch: string[];
}

const PRESETS: PresetMeta[] = [
  {
    value: "showroom_white",
    label: "展示間白",
    caption: "Showroom",
    description: "白平衡矯正、輕度提亮、降低飽和。乾淨明亮，主車不喧賓奪主。",
    swatch: ["#f3eee5", "#dad3c4", "#a89b85"],
  },
  {
    value: "outdoor_warm",
    label: "戶外暖調",
    caption: "Outdoor",
    description: "暖色偏移、輕微 vibrance、加對比。陽光感，金屬漆面有光澤。",
    swatch: ["#e8c882", "#c98a4e", "#7a3e1f"],
  },
  {
    value: "night_cold",
    label: "夜拍冷調",
    caption: "Night",
    description: "冷色偏移、提暗部、抑高光。霓虹反光突出，黑底自帶氛圍。",
    swatch: ["#5b7a92", "#26354d", "#0e1623"],
  },
];

const ASPECTS: { value: AutoCropAspect; label: string }[] = [
  { value: "original", label: "保留原比例" },
  { value: "3:2", label: "3:2 — 一般單眼" },
  { value: "4:3", label: "4:3 — 8891 / 平台預設" },
  { value: "16:9", label: "16:9 — 寬螢幕橫幅" },
  { value: "1:1", label: "1:1 — IG 方圖" },
  { value: "9:16", label: "9:16 — IG 限動" },
];

export interface StylePickerProps {
  value: StylePreset;
  onChange: (preset: StylePreset) => void;
  levelCorrect?: boolean;
  onLevelCorrectChange?: (next: boolean) => void;
  aspect?: AutoCropAspect;
  onAspectChange?: (next: AutoCropAspect) => void;
  disabled?: boolean;
  showOptions?: boolean;
}

export function StylePicker({
  value,
  onChange,
  levelCorrect,
  onLevelCorrectChange,
  aspect,
  onAspectChange,
  disabled = false,
  showOptions = false,
}: StylePickerProps) {
  return (
    <div className="style-picker-wrap">
      <div className="style-picker" role="radiogroup" aria-label="色調風格">
        {PRESETS.map((preset) => {
          const active = preset.value === value;
          return (
            <button
              key={preset.value}
              type="button"
              role="radio"
              aria-checked={active}
              className={`style-card${active ? " style-card--active" : ""}`}
              onClick={() => onChange(preset.value)}
              disabled={disabled}
            >
              <div className="style-card__caption">{preset.caption}</div>
              <div className="style-card__label">{preset.label}</div>
              <div className="style-card__swatch" aria-hidden>
                {preset.swatch.map((c) => (
                  <span key={c} style={{ background: c }} />
                ))}
              </div>
              <p className="style-card__desc">{preset.description}</p>
              <span className="style-card__check" aria-hidden>
                ✓
              </span>
            </button>
          );
        })}
      </div>

      {showOptions ? (
        <div className="style-options">
          <label className="style-options__row">
            <span className="style-options__caption mono">水平校正</span>
            <span className="style-options__control">
              <input
                type="checkbox"
                checked={levelCorrect ?? true}
                onChange={(e) => onLevelCorrectChange?.(e.target.checked)}
                disabled={disabled}
              />
              <span className="style-options__hint">
                偵測主水平線並旋正（角度誤判保護 ±5°）
              </span>
            </span>
          </label>
          <label className="style-options__row">
            <span className="style-options__caption mono">裁剪比例</span>
            <span className="style-options__control">
              <select
                className="style-options__select"
                value={aspect ?? "original"}
                onChange={(e) => onAspectChange?.(e.target.value as AutoCropAspect)}
                disabled={disabled}
              >
                {ASPECTS.map((a) => (
                  <option key={a.value} value={a.value}>
                    {a.label}
                  </option>
                ))}
              </select>
            </span>
          </label>
        </div>
      ) : null}
    </div>
  );
}
