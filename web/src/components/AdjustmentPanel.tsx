import { useRef, useState } from "react";
import type { CSSProperties } from "react";

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
  grade_preset: null,
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
  geometryBaseUrl: string;
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

type NumericAdjustmentKey = keyof Omit<AdjustmentParams, "hsl" | "source" | "grade_preset">;

export function AdjustmentPanel({
  params,
  presets,
  geometryBaseUrl,
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
  const [geometryOpen, setGeometryOpen] = useState(false);
  const setValue = (key: NumericAdjustmentKey, value: number) => {
    onChange({ ...params, [key]: value });
  };
  const resetValue = (key: NumericAdjustmentKey) => {
    onChange({ ...params, [key]: DEFAULT_ADJUSTMENT_PARAMS[key] });
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
        <button type="button" className="cta cta--quiet" onClick={() => resetValue("orientation")} disabled={busy || params.orientation === 0}>
          重設旋轉
        </button>
        <button type="button" className="cta cta--quiet" onClick={onRotateRight} disabled={busy}>
          向右旋轉 ↻
        </button>
      </div>

      <button
        type="button"
        className="geometry-launch"
        onClick={() => setGeometryOpen(true)}
        disabled={busy}
      >
        <span>
          構圖 / 幾何調整
          <small className="mono">
            水平 {params.rotation} · 裁切 {params.crop_zoom} · 變形 {params.distortion}
          </small>
        </span>
        <strong>開啟視窗</strong>
      </button>

      {geometryOpen && (
        <GeometryEditor
          params={params}
          baseUrl={geometryBaseUrl}
          busy={busy}
          onClose={() => setGeometryOpen(false)}
          onApply={(next) => {
            onChange(next);
            setGeometryOpen(false);
          }}
        />
      )}

      <div className="adjustment-panel__grid">
        <Slider label="曝光" value={params.exposure} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.exposure} min={-5} max={5} step={0.1} onChange={(v) => setValue("exposure", v)} onReset={() => resetValue("exposure")} />
        <Slider label="對比" value={params.contrast} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.contrast} onChange={(v) => setValue("contrast", v)} onReset={() => resetValue("contrast")} />
        <Slider label="亮部" value={params.highlights} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.highlights} onChange={(v) => setValue("highlights", v)} onReset={() => resetValue("highlights")} />
        <Slider label="暗部" value={params.shadows} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.shadows} onChange={(v) => setValue("shadows", v)} onReset={() => resetValue("shadows")} />
        <Slider label="色溫" value={params.temperature} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.temperature} onChange={(v) => setValue("temperature", v)} onReset={() => resetValue("temperature")} />
        <Slider label="色偏" value={params.tint} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.tint} onChange={(v) => setValue("tint", v)} onReset={() => resetValue("tint")} />
        <Slider label="飽和" value={params.saturation} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.saturation} onChange={(v) => setValue("saturation", v)} onReset={() => resetValue("saturation")} />
        <Slider label="自然飽和" value={params.vibrance} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.vibrance} onChange={(v) => setValue("vibrance", v)} onReset={() => resetValue("vibrance")} />
        <Slider label="清晰度" value={params.clarity} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.clarity} onChange={(v) => setValue("clarity", v)} onReset={() => resetValue("clarity")} />
        <Slider label="銳利化" value={params.sharpness} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.sharpness} onChange={(v) => setValue("sharpness", v)} onReset={() => resetValue("sharpness")} />
      </div>

      <details className="adjustment-panel__hsl">
        <summary>HSL</summary>
        {HSL_COLORS.map((color) => (
          <div key={color} className="adjustment-panel__hsl-row">
            <strong className="mono">{color}</strong>
            <Slider label="H" value={params.hsl[color].hue} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.hsl[color].hue} onChange={(v) => setHsl(color, "hue", v)} onReset={() => setHsl(color, "hue", DEFAULT_ADJUSTMENT_PARAMS.hsl[color].hue)} />
            <Slider label="S" value={params.hsl[color].saturation} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.hsl[color].saturation} onChange={(v) => setHsl(color, "saturation", v)} onReset={() => setHsl(color, "saturation", DEFAULT_ADJUSTMENT_PARAMS.hsl[color].saturation)} />
            <Slider label="L" value={params.hsl[color].luminance} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.hsl[color].luminance} onChange={(v) => setHsl(color, "luminance", v)} onReset={() => setHsl(color, "luminance", DEFAULT_ADJUSTMENT_PARAMS.hsl[color].luminance)} />
          </div>
        ))}
      </details>

      <div className="adjustment-panel__actions">
        <button type="button" className="cta cta--primary" onClick={onApplyCurrent} disabled={busy}>
          產生目前版本
        </button>
        <button type="button" className="cta" onClick={onApplySelected} disabled={busy}>
          產生已選版本
        </button>
        <button type="button" className="cta cta--quiet" onClick={onReset} disabled={busy}>
          重設
        </button>
      </div>
    </section>
  );
}

function GeometryEditor({
  params,
  baseUrl,
  busy,
  onClose,
  onApply,
}: {
  params: AdjustmentParams;
  baseUrl: string;
  busy: boolean;
  onClose: () => void;
  onApply: (params: AdjustmentParams) => void;
}) {
  const [draft, setDraft] = useState(params);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);
  const crop = cropFrame(draft.crop_zoom, draft.crop_x, draft.crop_y);
  const setValue = (key: NumericAdjustmentKey, value: number) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };
  const resetValue = (key: NumericAdjustmentKey) => {
    setValue(key, DEFAULT_ADJUSTMENT_PARAMS[key]);
  };
  const moveCropToPointer = (clientX: number, clientY: number) => {
    const shell = shellRef.current;
    if (!shell) return;
    const rect = shell.getBoundingClientRect();
    const zoom = Math.max(1, draft.crop_zoom);
    const cropWidth = 100 / zoom;
    const cropHeight = 100 / zoom;
    const maxLeft = 100 - cropWidth;
    const maxTop = 100 - cropHeight;
    if (maxLeft <= 0 && maxTop <= 0) return;
    const pointerX = ((clientX - rect.left) / rect.width) * 100;
    const pointerY = ((clientY - rect.top) / rect.height) * 100;
    const left = Math.max(0, Math.min(maxLeft, pointerX - cropWidth / 2));
    const top = Math.max(0, Math.min(maxTop, pointerY - cropHeight / 2));
    const cropX = maxLeft > 0 ? ((left - maxLeft / 2) / (maxLeft / 2)) * 100 : 0;
    const cropY = maxTop > 0 ? ((top - maxTop / 2) / (maxTop / 2)) * 100 : 0;
    setDraft((current) => ({
      ...current,
      crop_x: Number(cropX.toFixed(1)),
      crop_y: Number(cropY.toFixed(1)),
    }));
  };
  return (
    <div className="geometry-editor" role="dialog" aria-modal="true" aria-label="構圖與幾何調整">
      <div className="geometry-editor__panel">
        <header className="geometry-editor__head">
          <div>
            <strong>構圖 / 幾何調整</strong>
            <span className="mono">拖曳裁切框，完成後套用到目前照片</span>
          </div>
          <div className="geometry-editor__head-actions">
            <button type="button" className="cta cta--quiet" onClick={onClose}>取消</button>
            <button type="button" className="cta cta--primary" onClick={() => onApply(draft)}>完成</button>
          </div>
        </header>

        <div className="geometry-editor__stage">
          <div
            ref={shellRef}
            className="geometry-editor__image-shell"
            onPointerDown={(event) => {
              draggingRef.current = true;
              event.currentTarget.setPointerCapture(event.pointerId);
              moveCropToPointer(event.clientX, event.clientY);
            }}
            onPointerMove={(event) => {
              if (draggingRef.current) moveCropToPointer(event.clientX, event.clientY);
            }}
            onPointerUp={(event) => {
              draggingRef.current = false;
              event.currentTarget.releasePointerCapture(event.pointerId);
            }}
            onPointerCancel={() => {
              draggingRef.current = false;
            }}
          >
            <img src={baseUrl} alt="構圖基準" />
            <div className="geometry-editor__grid" aria-hidden>
              {Array.from({ length: 9 }).map((_, index) => (
                <span key={index} />
              ))}
            </div>
            <div className="geometry-editor__crop" style={crop}>
              <span />
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>

        <div className="geometry-editor__controls">
          <Slider label="水平" value={draft.rotation} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.rotation} min={-45} max={45} step={0.1} onChange={(v) => setValue("rotation", v)} onReset={() => resetValue("rotation")} />
          <Slider label="裁切" value={draft.crop_zoom} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.crop_zoom} min={1} max={3} step={0.01} onChange={(v) => setValue("crop_zoom", v)} onReset={() => resetValue("crop_zoom")} />
          <Slider label="裁切 X" value={draft.crop_x} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.crop_x} onChange={(v) => setValue("crop_x", v)} onReset={() => resetValue("crop_x")} />
          <Slider label="裁切 Y" value={draft.crop_y} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.crop_y} onChange={(v) => setValue("crop_y", v)} onReset={() => resetValue("crop_y")} />
          <Slider label="變形修正" value={draft.distortion} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.distortion} onChange={(v) => setValue("distortion", v)} onReset={() => resetValue("distortion")} />
        </div>
        {busy && <p className="geometry-editor__busy mono">正在產生版本...</p>}
      </div>
    </div>
  );
}

function cropFrame(zoom: number, x: number, y: number): CSSProperties {
  const width = 100 / Math.max(1, zoom);
  const height = 100 / Math.max(1, zoom);
  const maxLeft = 100 - width;
  const maxTop = 100 - height;
  const left = maxLeft / 2 + (x / 100) * (maxLeft / 2);
  const top = maxTop / 2 + (y / 100) * (maxTop / 2);
  return {
    left: `${Math.max(0, Math.min(maxLeft, left))}%`,
    top: `${Math.max(0, Math.min(maxTop, top))}%`,
    width: `${width}%`,
    height: `${height}%`,
  };
}

function Slider({
  label,
  value,
  defaultValue,
  min = -100,
  max = 100,
  step = 1,
  onChange,
  onReset,
}: {
  label: string;
  value: number;
  defaultValue: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number) => void;
  onReset: () => void;
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
      <button
        type="button"
        className="adjustment-slider__reset mono"
        onClick={onReset}
        disabled={value === defaultValue}
        aria-label={`重設${label}`}
      >
        歸零
      </button>
    </label>
  );
}
