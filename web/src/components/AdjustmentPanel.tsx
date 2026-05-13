import { useEffect, useRef, useState } from "react";
import type { CSSProperties, PointerEvent } from "react";

import type { AdjustmentParams, AdjustmentPreset, HslColor } from "@/types";
import {
  CROP_HANDLES,
  applyCropFrame,
  containedImageFrame,
  cropFrame,
  moveCropFrame,
  resizeCropFrame,
} from "@/utils/geometryCrop";
import type { CropHandle, Frame } from "@/utils/geometryCrop";

import "./AdjustmentPanel.css";

const HSL_COLORS: HslColor[] = ["red", "orange", "yellow", "green", "blue", "purple"];
const PREVIEW_PERSPECTIVE_PX = 900;
const PREVIEW_DISTORTION_DEGREES = 0.08;

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
  distortion_x: 0,
  distortion_y: 0,
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
  selectedCount: number;
  onChange: (params: AdjustmentParams) => void;
  onApplyCurrent: () => void;
  onApplySelected: () => void;
  onClearCurrent: () => void;
  onClearSelected: () => void;
  onSavePreset: (name: string) => void;
  onLoadPreset: (preset: AdjustmentPreset) => void;
  onOpenPresetManager: () => void;
  onRotateLeft: () => void;
  onRotateRight: () => void;
};

type NumericAdjustmentKey = keyof Omit<AdjustmentParams, "hsl" | "source" | "grade_preset">;
type CropInteraction = {
  mode: "move" | "resize";
  handle?: CropHandle;
  pointerId: number;
  startX: number;
  startY: number;
  startCrop: Frame;
  imageFrame: Frame;
};

export function AdjustmentPanel({
  params,
  presets,
  geometryBaseUrl,
  busy,
  selectedCount,
  onChange,
  onApplyCurrent,
  onApplySelected,
  onClearCurrent,
  onClearSelected,
  onSavePreset,
  onLoadPreset,
  onOpenPresetManager,
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
          <option value="">— 選 preset 載入到目前照片 —</option>
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
          儲存目前數值
        </button>
        <button
          type="button"
          className="cta cta--quiet"
          onClick={onOpenPresetManager}
          disabled={busy}
        >
          ⚙ 管理
        </button>
      </div>
      <p className="adjustment-panel__preset-hint">
        選 preset = 把它的數值複製到目前照片的 sliders。
        刪除 preset 只移除 template，<strong>不會動到任何照片</strong>。
      </p>

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
            水平 {params.rotation} · 裁切 {params.crop_zoom} · 透視 H {distortionXValue(params)} / V {params.distortion_y ?? 0}
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

      <div className="adjustment-panel__action-group">
        <p className="adjustment-panel__action-label mono">套用微調</p>
        <div className="adjustment-panel__actions">
          <button type="button" className="cta cta--primary" onClick={onApplyCurrent} disabled={busy}>
            套用微調到目前照片
          </button>
          <button
            type="button"
            className="cta"
            onClick={onApplySelected}
            disabled={busy || selectedCount === 0}
          >
            套用微調到已選 {selectedCount} 張
          </button>
        </div>
        <p className="adjustment-panel__action-hint">
          會新增手動 v?，舊版本不會被覆蓋。
        </p>
      </div>

      <div className="adjustment-panel__action-group">
        <p className="adjustment-panel__action-label mono">清空微調</p>
        <div className="adjustment-panel__actions">
          <button type="button" className="cta" onClick={onClearCurrent} disabled={busy}>
            清空目前照片的微調
          </button>
          <button
            type="button"
            className="cta"
            onClick={onClearSelected}
            disabled={busy || selectedCount === 0}
          >
            清空已選 {selectedCount} 張的微調
          </button>
        </div>
        <p className="adjustment-panel__action-hint">
          會刪除這些照片所有手動版本，視覺切回 AI 版本或原圖。<strong>無法復原</strong>。
        </p>
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
  const [draft, setDraft] = useState(() => withAdjustmentDefaults(params));
  const shellRef = useRef<HTMLDivElement | null>(null);
  const [imageSize, setImageSize] = useState({ width: 1, height: 1 });
  const [shellSize, setShellSize] = useState({ width: 1, height: 1 });
  const interactionRef = useRef<CropInteraction | null>(null);
  const imageFrame = containedImageFrame(shellSize, imageSize);
  const crop = cropFrame(draft.crop_zoom, draft.crop_x, draft.crop_y, imageFrame);
  const cropStyle = frameToStyle(crop, shellSize);
  const imageLayerStyle: CSSProperties = {
    ...frameToStyle(imageFrame, shellSize),
    ...geometryPreviewStyle(draft),
  };
  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;
    const update = () => {
      const rect = shell.getBoundingClientRect();
      setShellSize({ width: Math.max(1, rect.width), height: Math.max(1, rect.height) });
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(shell);
    return () => observer.disconnect();
  }, []);
  const setValue = (key: NumericAdjustmentKey, value: number) => {
    setDraft((current) => syncLegacyDistortion({ ...current, [key]: value }, key, value));
  };
  const resetValue = (key: NumericAdjustmentKey) => {
    setValue(key, DEFAULT_ADJUSTMENT_PARAMS[key]);
  };
  const startCropInteraction = (
    event: PointerEvent<HTMLElement>,
    mode: CropInteraction["mode"],
    handle?: CropHandle,
  ) => {
    const shell = shellRef.current;
    if (!shell) return;
    event.preventDefault();
    event.stopPropagation();
    shell.setPointerCapture(event.pointerId);
    interactionRef.current = {
      mode,
      handle,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startCrop: crop,
      imageFrame,
    };
  };
  const updateCropInteraction = (event: PointerEvent<HTMLDivElement>) => {
    const interaction = interactionRef.current;
    if (!interaction || interaction.pointerId !== event.pointerId) return;
    const dx = event.clientX - interaction.startX;
    const dy = event.clientY - interaction.startY;
    const nextCrop = interaction.mode === "move"
      ? moveCropFrame(interaction.startCrop, interaction.imageFrame, dx, dy)
      : resizeCropFrame(
          interaction.startCrop,
          interaction.imageFrame,
          interaction.handle ?? "se",
          event.clientX,
          event.clientY,
        );
    setDraft((current) => applyCropFrame(current, nextCrop, interaction.imageFrame));
  };
  const stopCropInteraction = (event: PointerEvent<HTMLDivElement>) => {
    if (interactionRef.current?.pointerId !== event.pointerId) return;
    interactionRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
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
            onPointerMove={updateCropInteraction}
            onPointerUp={stopCropInteraction}
            onPointerCancel={stopCropInteraction}
          >
            <div className="geometry-editor__image-layer" style={imageLayerStyle}>
              <img
                src={baseUrl}
                alt="構圖基準"
                onLoad={(event) => {
                  setImageSize({
                    width: Math.max(1, event.currentTarget.naturalWidth),
                    height: Math.max(1, event.currentTarget.naturalHeight),
                  });
                }}
              />
              <div className="geometry-editor__grid" aria-hidden>
                {Array.from({ length: 9 }).map((_, index) => (
                  <span key={index} />
                ))}
              </div>
            </div>
            <div
              className="geometry-editor__crop"
              style={cropStyle}
              onPointerDown={(event) => startCropInteraction(event, "move")}
            >
              <span />
              <span />
              <span />
              <span />
              {CROP_HANDLES.map((handle) => (
                <button
                  key={handle}
                  type="button"
                  className={`geometry-editor__handle geometry-editor__handle--${handle}`}
                  aria-label={`調整裁切框 ${handle}`}
                  onPointerDown={(event) => startCropInteraction(event, "resize", handle)}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="geometry-editor__controls">
          <Slider label="水平校正" value={draft.rotation} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.rotation} min={-45} max={45} step={0.1} onChange={(v) => setValue("rotation", v)} onReset={() => resetValue("rotation")} />
          <Slider label="裁切" value={draft.crop_zoom} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.crop_zoom} min={1} max={3} step={0.01} onChange={(v) => setValue("crop_zoom", v)} onReset={() => resetValue("crop_zoom")} />
          <Slider label="裁切 X" value={draft.crop_x} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.crop_x} onChange={(v) => setValue("crop_x", v)} onReset={() => resetValue("crop_x")} />
          <Slider label="裁切 Y" value={draft.crop_y} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.crop_y} onChange={(v) => setValue("crop_y", v)} onReset={() => resetValue("crop_y")} />
          <Slider label="水平透視" value={draft.distortion_x} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.distortion_x} onChange={(v) => setValue("distortion_x", v)} onReset={() => resetValue("distortion_x")} />
          <Slider label="垂直透視" value={draft.distortion_y} defaultValue={DEFAULT_ADJUSTMENT_PARAMS.distortion_y} onChange={(v) => setValue("distortion_y", v)} onReset={() => resetValue("distortion_y")} />
        </div>
        {busy && <p className="geometry-editor__busy mono">正在產生版本...</p>}
      </div>
    </div>
  );
}

function frameToStyle(frame: Frame, shell: { width: number; height: number }): CSSProperties {
  return {
    left: `${(frame.left / shell.width) * 100}%`,
    top: `${(frame.top / shell.height) * 100}%`,
    width: `${(frame.width / shell.width) * 100}%`,
    height: `${(frame.height / shell.height) * 100}%`,
  };
}

function withAdjustmentDefaults(params: AdjustmentParams): AdjustmentParams {
  const raw = params as Partial<AdjustmentParams>;
  const distortionX = distortionXValue(params);
  return {
    ...structuredClone(DEFAULT_ADJUSTMENT_PARAMS),
    ...params,
    distortion: distortionX,
    distortion_x: distortionX,
    distortion_y: raw.distortion_y ?? DEFAULT_ADJUSTMENT_PARAMS.distortion_y,
  };
}

function distortionXValue(params: Partial<AdjustmentParams>): number {
  if (typeof params.distortion_x === "number" && (params.distortion_x !== 0 || !params.distortion)) {
    return params.distortion_x;
  }
  return params.distortion ?? DEFAULT_ADJUSTMENT_PARAMS.distortion_x;
}

function syncLegacyDistortion(
  params: AdjustmentParams,
  key: NumericAdjustmentKey,
  value: number,
): AdjustmentParams {
  if (key === "distortion" || key === "distortion_x") {
    return { ...params, distortion: value, distortion_x: value };
  }
  return params;
}

function geometryPreviewStyle(params: AdjustmentParams): CSSProperties {
  const horizontal = params.distortion_x ?? params.distortion;
  const vertical = params.distortion_y ?? 0;
  return {
    transform: [
      `perspective(${PREVIEW_PERSPECTIVE_PX}px)`,
      `rotateX(${vertical * PREVIEW_DISTORTION_DEGREES}deg)`,
      `rotateY(${-horizontal * PREVIEW_DISTORTION_DEGREES}deg)`,
      `rotate(${params.rotation}deg)`,
    ].join(" "),
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
