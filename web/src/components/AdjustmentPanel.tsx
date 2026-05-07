import type { AdjustmentParams, AdjustmentPreset, HslColor } from "@/types";

import "./AdjustmentPanel.css";

const HSL_COLORS: HslColor[] = ["red", "orange", "yellow", "green", "blue", "purple"];

function orientationLabel(value: number): string {
  const normalized = ((Math.round(value) % 360) + 360) % 360;
  if (normalized === 90) return "右轉 90°";
  if (normalized === 180) return "旋轉 180°";
  if (normalized === 270) return "左轉 90°";
  return "未旋轉";
}

export const DEFAULT_ADJUSTMENT_PARAMS: AdjustmentParams = {
  exposure: 0,
  contrast: 0,
  highlights: 0,
  shadows: 0,
  temperature: 0,
  tint: 0,
  saturation: 0,
  vibrance: 0,
  clarity: 0,
  sharpness: 0,
  orientation: 0,
  rotation: 0,
  crop_zoom: 1,
  crop_x: 0,
  crop_y: 0,
  distortion: 0,
  hsl: {
    red: { hue: 0, saturation: 0, luminance: 0 },
    orange: { hue: 0, saturation: 0, luminance: 0 },
    yellow: { hue: 0, saturation: 0, luminance: 0 },
    green: { hue: 0, saturation: 0, luminance: 0 },
    blue: { hue: 0, saturation: 0, luminance: 0 },
    purple: { hue: 0, saturation: 0, luminance: 0 },
  },
};

type Props = {
  params: AdjustmentParams;
  presets: AdjustmentPreset[];
  busy: boolean;
  onChange: (params: AdjustmentParams) => void;
  onApplyCurrent: () => void;
  onApplySelected: () => void;
  onReset: () => void;
  onSavePreset: (name: string) => void;
  onLoadPreset: (preset: AdjustmentPreset) => void;
  onDeletePreset: (preset: AdjustmentPreset) => void;
  onRotateLeft: () => void;
  onRotateRight: () => void;
};

export function AdjustmentPanel({
  params,
  presets,
  busy,
  onChange,
  onApplyCurrent,
  onApplySelected,
  onReset,
  onSavePreset,
  onLoadPreset,
  onDeletePreset,
  onRotateLeft,
  onRotateRight,
}: Props) {
  const setValue = (key: keyof Omit<AdjustmentParams, "hsl">, value: number) => {
    onChange({ ...params, [key]: value });
  };
  const setHsl = (
    color: HslColor,
    key: "hue" | "saturation" | "luminance",
    value: number,
  ) => {
    onChange({
      ...params,
      hsl: {
        ...params.hsl,
        [color]: { ...params.hsl[color], [key]: value },
      },
    });
  };
  return (
    <section className="adjustment-panel section">
      <header className="section__head">
        <h2 className="section__title">手動微調</h2>
        <span className="section__meta mono">LIVE PREVIEW</span>
      </header>

      <div className="adjustment-panel__presets">
        <select
          className="adjustment-panel__select mono"
          defaultValue=""
          onChange={(event) => {
            const preset = presets.find((item) => item.id === event.target.value);
            if (preset) onLoadPreset(preset);
            event.target.value = "";
          }}
        >
          <option value="">載入 preset...</option>
          {presets.map((preset) => (
            <option key={preset.id} value={preset.id}>
              {preset.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="cta cta--quiet"
          onClick={() => {
            const name = window.prompt("Preset 名稱");
            if (name?.trim()) onSavePreset(name.trim());
          }}
          disabled={busy}
        >
          儲存 preset
        </button>
        <select
          className="adjustment-panel__select mono"
          defaultValue=""
          onChange={(event) => {
            const preset = presets.find((item) => item.id === event.target.value);
            if (preset) onDeletePreset(preset);
            event.target.value = "";
          }}
          disabled={busy || presets.length === 0}
        >
          <option value="">刪除 preset...</option>
          {presets.map((preset) => (
            <option key={preset.id} value={preset.id}>
              {preset.name}
            </option>
          ))}
        </select>
      </div>

      <div className="adjustment-panel__actions adjustment-panel__actions--rotate">
        <button type="button" className="cta cta--quiet" onClick={onRotateLeft} disabled={busy}>
          ↺ 向左旋轉
        </button>
        <span className="section__meta mono">{orientationLabel(params.orientation)}</span>
        <button type="button" className="cta cta--quiet" onClick={onRotateRight} disabled={busy}>
          向右旋轉 ↻
        </button>
      </div>

      <div className="adjustment-panel__grid">
        <Slider label="水平" value={params.rotation} min={-45} max={45} step={0.1} onChange={(v) => setValue("rotation", v)} />
        <Slider label="裁切" value={params.crop_zoom} min={1} max={3} step={0.01} onChange={(v) => setValue("crop_zoom", v)} />
        <Slider label="裁切 X" value={params.crop_x} onChange={(v) => setValue("crop_x", v)} />
        <Slider label="裁切 Y" value={params.crop_y} onChange={(v) => setValue("crop_y", v)} />
        <Slider label="變形修正" value={params.distortion} onChange={(v) => setValue("distortion", v)} />
        <Slider label="曝光" value={params.exposure} min={-5} max={5} step={0.1} onChange={(v) => setValue("exposure", v)} />
        <Slider label="對比" value={params.contrast} onChange={(v) => setValue("contrast", v)} />
        <Slider label="亮部" value={params.highlights} onChange={(v) => setValue("highlights", v)} />
        <Slider label="暗部" value={params.shadows} onChange={(v) => setValue("shadows", v)} />
        <Slider label="色溫" value={params.temperature} onChange={(v) => setValue("temperature", v)} />
        <Slider label="色偏" value={params.tint} onChange={(v) => setValue("tint", v)} />
        <Slider label="飽和" value={params.saturation} onChange={(v) => setValue("saturation", v)} />
        <Slider label="自然飽和" value={params.vibrance} onChange={(v) => setValue("vibrance", v)} />
        <Slider label="清晰度" value={params.clarity} onChange={(v) => setValue("clarity", v)} />
        <Slider label="銳利化" value={params.sharpness} onChange={(v) => setValue("sharpness", v)} />
      </div>

      <details className="adjustment-panel__hsl">
        <summary>HSL</summary>
        {HSL_COLORS.map((color) => (
          <div key={color} className="adjustment-panel__hsl-row">
            <strong className="mono">{color}</strong>
            <Slider label="H" value={params.hsl[color].hue} onChange={(v) => setHsl(color, "hue", v)} />
            <Slider label="S" value={params.hsl[color].saturation} onChange={(v) => setHsl(color, "saturation", v)} />
            <Slider label="L" value={params.hsl[color].luminance} onChange={(v) => setHsl(color, "luminance", v)} />
          </div>
        ))}
      </details>

      <div className="adjustment-panel__actions">
        <button type="button" className="cta cta--primary" onClick={onApplyCurrent} disabled={busy}>
          套用目前照片
        </button>
        <button type="button" className="cta" onClick={onApplySelected} disabled={busy}>
          套用到已選照片
        </button>
        <button type="button" className="cta cta--quiet" onClick={onReset} disabled={busy}>
          重設
        </button>
      </div>
    </section>
  );
}

function Slider({
  label,
  value,
  min = -100,
  max = 100,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="adjustment-slider">
      <span>{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <output className="mono">{value}</output>
    </label>
  );
}
