import type { AspectRatio } from "@/types";

import "./AspectPicker.css";

interface Option {
  value: AspectRatio;
  label: string;
  caption: string;
}

const OPTIONS: Option[] = [
  { value: "original", label: "原始", caption: "Keep" },
  { value: "ratio_3_2", label: "3 : 2", caption: "Classic" },
  { value: "ratio_4_3", label: "4 : 3", caption: "Print" },
  { value: "ratio_16_9", label: "16 : 9", caption: "Wide" },
  { value: "ratio_1_1", label: "1 : 1", caption: "IG Feed" },
  { value: "ratio_9_16", label: "9 : 16", caption: "Reels" },
];

export interface AspectPickerProps {
  value: AspectRatio;
  onChange: (next: AspectRatio) => void;
  disabled?: boolean;
}

export function AspectPicker({ value, onChange, disabled = false }: AspectPickerProps) {
  return (
    <div className="aspect-picker" role="radiogroup" aria-label="裁剪比例">
      {OPTIONS.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            className={`aspect-pill${active ? " aspect-pill--active" : ""}`}
            onClick={() => onChange(opt.value)}
            disabled={disabled}
          >
            <span className="aspect-pill__caption">{opt.caption}</span>
            <span className="aspect-pill__label">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
