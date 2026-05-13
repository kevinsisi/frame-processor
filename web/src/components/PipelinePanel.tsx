import { AspectPicker } from "@/components/AspectPicker";
import { StylePicker, type StylePreset } from "@/components/StylePicker";
import type {
  AspectRatio,
  ChromaCleanStrength,
  CplStrength,
  DetailPreserveStrength,
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
  chromaCleanStrength: ChromaCleanStrength;
  detailPreserveStrength: DetailPreserveStrength;
  onPresetChange: (preset: StylePreset) => void;
  onDenoiseChange: (denoise: DenoiseStrength) => void;
  onLensDistortChange: (enabled: boolean) => void;
  onLevelCorrectChange: (enabled: boolean) => void;
  onAspectChange: (aspect: AspectRatio) => void;
  onCplStrengthChange: (strength: CplStrength) => void;
  onChromaCleanStrengthChange: (strength: ChromaCleanStrength) => void;
  onDetailPreserveStrengthChange: (strength: DetailPreserveStrength) => void;
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

const CHROMA_CLEAN_OPTIONS: { value: ChromaCleanStrength; label: string; caption: string }[] = [
  { value: "none", label: "關閉", caption: "Off" },
  { value: "low", label: "輕度", caption: "Low" },
  { value: "medium", label: "中度", caption: "Med" },
  { value: "high", label: "重度", caption: "High" },
];

const DETAIL_PRESERVE_OPTIONS: { value: DetailPreserveStrength; label: string; caption: string }[] = [
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
  chromaCleanStrength,
  detailPreserveStrength,
  onPresetChange,
  onDenoiseChange,
  onLensDistortChange,
  onLevelCorrectChange,
  onAspectChange,
  onCplStrengthChange,
  onChromaCleanStrengthChange,
  onDetailPreserveStrengthChange,
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
      chroma_clean_strength: chromaCleanStrength,
      detail_preserve_strength: detailPreserveStrength,
    });
  }

  return (
    <section className="pipeline">
      <header className="pipeline__head">
        <h3 className="pipeline__title">處理設定</h3>
        <p className="pipeline__lede mono">
          順序：降噪 → 偽色雜色修正 → 細節保留 → 廣角矯正 → 水平校正 → 自動裁剪 → 車內 CPL Look → 色調
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
          <p className="pipeline__hint">預設關閉；照片已被手機或相機校正時，不需要為了降噪強制套幾何。</p>
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
        <div className="pipeline__row-title-wrap">
          <h4 className="pipeline__row-title">Chroma Clean / 偽色雜色修正</h4>
          <span className="pipeline__hint">針對暗部彩色顆粒、紅綠紫色斑與低飽和偽色；保護黃色安全帶與氛圍燈。</span>
        </div>
        <div className="pipeline__chips">
          {CHROMA_CLEAN_OPTIONS.map((opt) => {
            const active = opt.value === chromaCleanStrength;
            return (
              <button
                key={opt.value}
                type="button"
                className={`pipeline__chip${active ? " pipeline__chip--active" : ""}`}
                onClick={() => onChromaCleanStrengthChange(opt.value)}
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
        <div className="pipeline__row-title-wrap">
          <h4 className="pipeline__row-title">Detail Preserve / 細節保留</h4>
          <span className="pipeline__hint">只回填原圖亮度紋理，不生成假細節；避免把暗部彩色噪點加回來。</span>
        </div>
        <div className="pipeline__chips">
          {DETAIL_PRESERVE_OPTIONS.map((opt) => {
            const active = opt.value === detailPreserveStrength;
            return (
              <button
                key={opt.value}
                type="button"
                className={`pipeline__chip${active ? " pipeline__chip--active" : ""}`}
                onClick={() => onDetailPreserveStrengthChange(opt.value)}
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
          {busy ? "AI 處理中…" : `開始 AI 處理已選 ${selectedCount} 張`}
        </button>
        <p className="pipeline__action-hint mono">
          會新增 AI v?，已存在的 AI 版本與手動微調版本不影響。每張數十秒～數分鐘。
        </p>
      </footer>
    </section>
  );
}
