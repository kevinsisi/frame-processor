import "./StylePicker.css";

// Mirrors models/enums.py:ColorGradePreset. Backend processing arrives in
// v0.2; for the walking skeleton this picker is wired to local state only,
// so the UI is honest about state by carrying a small "v0.2" hint chip.
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

export interface StylePickerProps {
  value: StylePreset;
  onChange: (preset: StylePreset) => void;
}

export function StylePicker({ value, onChange }: StylePickerProps) {
  return (
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
  );
}
