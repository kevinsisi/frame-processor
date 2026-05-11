import { AspectPicker } from "@/components/AspectPicker";
import { StylePicker, type StylePreset } from "@/components/StylePicker";
import type {
  AspectRatio,
  CplStrength,
  DenoiseStrength,
  ProcessingJobCreate,
} from "@/types";

import "./PipelinePanel.css";

export interface PipelinePanelProps {
  selectedCount: number;
  totalCount: number;
  busy: boolean;
  preset: StylePreset;
  denoise: DenoiseStrength;
  lensDistort: boolean;
  levelCorrect: boolean;
  aspect: AspectRatio;
  cplStrength: CplStrength;
  onPresetChange: (preset: StylePreset) => void;
  onDenoiseChange: (denoise: DenoiseStrength) => void;
  onLensDistortChange: (enabled: boolean) => void;
  onLevelCorrectChange: (enabled: boolean) => void;
  onAspectChange: (aspect: AspectRatio) => void;
  onCplStrengthChange: (strength: CplStrength) => void;
  onSubmit: (payload: ProcessingJobCreate) => void;
}

const DENOISE_OPTIONS: { value: DenoiseStrength; label: string; caption: string }[] = [
  { value: "none", label: "關閉", caption: "Off" },
  { value: "light", label: "輕度", caption: "Light" },
  { value: "medium", label: "中度", caption: "Med" },
  { value: "heavy", label: "重度", caption: "Heavy" },
];

const CPL_OPTIONS: { value: CplStrength; label: string; caption: string }[] = [
  { value: "none", label: "關閉", caption: "Off" },
  { value: "low", label: "輕度", caption: "Low" },
  { value: "medium", label: "中度", caption: "Med" },
  { value: "high", label: "重度", caption: "High" },
];

export function PipelinePanel({
  selectedCount,
  totalCount,
  busy,
  preset,
  denoise,
  lensDistort,
  levelCorrect,
  aspect,
  cplStrength,
  onPresetChange,
  onDenoiseChange,
  onLensDistortChange,
  onLevelCorrectChange,
  onAspectChange,
  onCplStrengthChange,
  onSubmit,
}: PipelinePanelProps) {
  function handleSubmit() {
    onSubmit({
      preset,
      denoise_strength: denoise,
      lens_distort_correct: lensDistort,
      level_correct: levelCorrect,
      auto_crop_aspect: aspect === "original" ? null : aspect,
      cpl_strength: cplStrength,
    });
  }

  return (
    <section className="pipeline">
      <header className="pipeline__head">
        <h3 className="pipeline__title">處理設定</h3>
        <p className="pipeline__lede mono">
          順序：降噪 → 廣角矯正 → 水平校正 → 自動裁剪 → 車內 CPL Look → 色調
        </p>
      </header>

      <div className="pipeline__row">
        <h4 className="pipeline__row-title">色調風格</h4>
        <StylePicker value={preset} onChange={onPresetChange} disabled={busy} />
      </div>

      <div className="pipeline__row pipeline__row--grid">
        <div className="pipeline__field">
          <h4 className="pipeline__row-title">AI 降噪（NAFNet）</h4>
          <div className="pipeline__chips">
            {DENOISE_OPTIONS.map((opt) => {
              const active = opt.value === denoise;
              return (
                <button
                  key={opt.value}
                  type="button"
                  className={`pipeline__chip${active ? " pipeline__chip--active" : ""}`}
                  onClick={() => onDenoiseChange(opt.value)}
                  disabled={busy}
                >
                  <span className="pipeline__chip-caption mono">{opt.caption}</span>
                  <span className="pipeline__chip-label">{opt.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="pipeline__field">
          <h4 className="pipeline__row-title">幾何矯正</h4>
          <label className="pipeline__check">
            <input
              type="checkbox"
              checked={lensDistort}
              onChange={(e) => onLensDistortChange(e.target.checked)}
              disabled={busy}
            />
            <span>廣角畸變矯正（barrel undistort）</span>
          </label>
          <label className="pipeline__check">
            <input
              type="checkbox"
              checked={levelCorrect}
              onChange={(e) => onLevelCorrectChange(e.target.checked)}
              disabled={busy}
            />
            <span>水平校正（Gemini Vision）</span>
          </label>
        </div>
      </div>

      <div className="pipeline__row">
        <div className="pipeline__row-title-wrap">
          <h4 className="pipeline__row-title">CPL Look / 反光抑制</h4>
          <span className="pipeline__hint">針對黑色亮面飾板、儀表玻璃、中控螢幕與車窗反光；不會還原白爆細節。</span>
        </div>
        <div className="pipeline__chips">
          {CPL_OPTIONS.map((opt) => {
            const active = opt.value === cplStrength;
            return (
              <button
                key={opt.value}
                type="button"
                className={`pipeline__chip${active ? " pipeline__chip--active" : ""}`}
                onClick={() => onCplStrengthChange(opt.value)}
                disabled={busy}
              >
                <span className="pipeline__chip-caption mono">{opt.caption}</span>
                <span className="pipeline__chip-label">{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="pipeline__row">
        <h4 className="pipeline__row-title">自動裁剪比例</h4>
        <AspectPicker value={aspect} onChange={onAspectChange} disabled={busy} />
      </div>

      <footer className="pipeline__foot">
        <span className="pipeline__count mono">
          將處理 {selectedCount} / {totalCount} 張
        </span>
        <button
          type="button"
          className="cta cta--primary"
          onClick={handleSubmit}
          disabled={busy || selectedCount === 0}
        >
          {busy ? "產生中…" : "開始產生"}
        </button>
      </footer>
    </section>
  );
}
