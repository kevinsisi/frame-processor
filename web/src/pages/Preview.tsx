import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import {
  AdjustmentPanel,
  DEFAULT_ADJUSTMENT_PARAMS,
} from "@/components/AdjustmentPanel";
import { BeforeAfter } from "@/components/BeforeAfter";
import { PhotoGrid } from "@/components/PhotoGrid";
import { PipelinePanel } from "@/components/PipelinePanel";
import { Spinner } from "@/components/Spinner";
import { useToast } from "@/components/Toast";
import type {
  ColorGradePreset,
  AdjustmentParams,
  AdjustmentJob,
  AdjustmentPreset,
  ProcessingJob,
  ProcessingJobCreate,
  ProjectDetail,
} from "@/types";

import "./Preview.css";

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("failed to read preview"));
    reader.readAsDataURL(blob);
  });
}

function defaultSelectedPhotoIds(project: ProjectDetail): Set<string> {
  const adjusted = project.photos
    .filter((photo) => photo.adjustment_params || (photo.adjustment_versions ?? []).length > 0)
    .map((photo) => photo.id);
  return new Set(adjusted.length > 0 ? adjusted : project.photos.map((photo) => photo.id));
}

export default function PreviewPage() {
  const { projectId } = useParams();
  const { push: toast } = useToast();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activePhotoId, setActivePhotoId] = useState<string | null>(null);
  const [adjustmentParams, setAdjustmentParams] = useState<AdjustmentParams>(() =>
    structuredClone(DEFAULT_ADJUSTMENT_PARAMS),
  );
  const [preview, setPreview] = useState<{ photoId: string; url: string } | null>(null);
  const [basePreview, setBasePreview] = useState<{ photoId: string; url: string } | null>(null);
  const [presets, setPresets] = useState<AdjustmentPreset[]>([]);
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [adjustmentJob, setAdjustmentJob] = useState<AdjustmentJob | null>(null);
  const [pipelineBusy, setPipelineBusy] = useState(false);
  const [adjustmentBusy, setAdjustmentBusy] = useState(false);
  const [draftDirty, setDraftDirty] = useState(false);
  const pollRef = useRef<number | null>(null);
  const adjustmentPollRef = useRef<number | null>(null);
  const previewRequestRef = useRef(0);
  const basePreviewRequestRef = useRef(0);
  const draftRequestRef = useRef(0);
  const adjustmentParamsRef = useRef(adjustmentParams);

  function updateAdjustmentParams(
    params: AdjustmentParams,
    options: { persist?: boolean } = {},
  ) {
    adjustmentParamsRef.current = params;
    setAdjustmentParams(params);
    if (options.persist !== false) setDraftDirty(true);
  }

  function reload() {
    if (!projectId) return;
    api
      .getProject(projectId)
      .then((p) => setProject(p))
      .catch((err) => setError(String(err)));
  }

  function reloadPresets() {
    if (!projectId) return;
    api
      .listAdjustmentPresets(projectId)
      .then(setPresets)
      .catch((err) => toast(`讀取 preset 失敗：${String(err)}`, "error"));
  }

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    setProject(null);
    setError(null);
    api
      .getProject(projectId)
      .then((p) => {
        setProject(p);
        setSelected(defaultSelectedPhotoIds(p));
        setActivePhotoId(
          p.photos.find((ph) => Object.keys(ph.processed_paths ?? {}).length > 0)?.id ??
            p.photos[0]?.id ??
            null,
        );
        reloadPresets();
      })
      .catch((err) => setError(String(err)));
  }, [projectId]);

  useEffect(() => {
    adjustmentParamsRef.current = adjustmentParams;
  }, [adjustmentParams]);

  useEffect(() => {
    if (!project || !activePhotoId) return;
    const active = project.photos.find((photo) => photo.id === activePhotoId);
    updateAdjustmentParams(
      active?.adjustment_params
        ? { ...structuredClone(DEFAULT_ADJUSTMENT_PARAMS), ...active.adjustment_params }
        : structuredClone(DEFAULT_ADJUSTMENT_PARAMS),
      { persist: false },
    );
    setDraftDirty(false);
  }, [activePhotoId, project]);

  useEffect(() => {
    if (!activePhotoId || !draftDirty) return;
    const requestId = ++draftRequestRef.current;
    const handle = window.setTimeout(async () => {
      try {
        await api.saveAdjustmentDraft(activePhotoId, adjustmentParams);
        if (draftRequestRef.current === requestId) setDraftDirty(false);
      } catch (err) {
        console.warn("save adjustment draft failed", err);
      }
    }, 500);
    return () => window.clearTimeout(handle);
  }, [activePhotoId, adjustmentParams, draftDirty]);

  useEffect(() => {
    if (!activePhotoId) {
      setPreview(null);
      return;
    }
    const requestId = ++previewRequestRef.current;
    setPreview(null);
    const handle = window.setTimeout(async () => {
      try {
        const blob = await api.previewAdjustment(activePhotoId, adjustmentParams);
        const url = await blobToDataUrl(blob);
        if (previewRequestRef.current !== requestId) {
          return;
        }
        setPreview({ photoId: activePhotoId, url });
      } catch (err) {
        console.warn("adjustment preview failed", err);
      }
    }, 120);
    return () => window.clearTimeout(handle);
  }, [activePhotoId, adjustmentParams]);

  useEffect(() => {
    if (!activePhotoId || adjustmentParams.orientation === 0) {
      basePreviewRequestRef.current += 1;
      setBasePreview(null);
      return;
    }
    const requestId = ++basePreviewRequestRef.current;
    const params = {
      ...structuredClone(DEFAULT_ADJUSTMENT_PARAMS),
      orientation: adjustmentParams.orientation,
    };
    const handle = window.setTimeout(async () => {
      try {
        const blob = await api.previewAdjustment(activePhotoId, params);
        const url = await blobToDataUrl(blob);
        if (basePreviewRequestRef.current !== requestId) {
          return;
        }
        setBasePreview({ photoId: activePhotoId, url });
      } catch (err) {
        console.warn("base orientation preview failed", err);
      }
    }, 60);
    return () => window.clearTimeout(handle);
  }, [activePhotoId, adjustmentParams.orientation]);

  useEffect(() => {
    return () => {
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
      if (adjustmentPollRef.current !== null) {
        window.clearInterval(adjustmentPollRef.current);
      }
    };
  }, []);

  function toggle(photoId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(photoId)) {
        next.delete(photoId);
      } else {
        next.add(photoId);
      }
      return next;
    });
  }

  function selectAll() {
    if (!project) return;
    setSelected(new Set(project.photos.map((p) => p.id)));
  }

  function selectAdjusted() {
    if (!project) return;
    setSelected(defaultSelectedPhotoIds(project));
  }

  function selectNone() {
    setSelected(new Set());
  }

  async function handleSubmit(payload: ProcessingJobCreate) {
    if (!projectId || !project) return;
    setPipelineBusy(true);
    try {
      const created = await api.createProcessingJob(projectId, {
        ...payload,
        photo_ids: Array.from(selected),
      });
      setJob(created);
      toast(`已開始處理，共 ${created.total} 張`, "info");
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
      pollRef.current = window.setInterval(async () => {
        try {
          const next = await api.getProcessingJob(created.id);
          setJob(next);
          if (next.status === "done" || next.status === "failed") {
            if (pollRef.current !== null) {
              window.clearInterval(pollRef.current);
              pollRef.current = null;
            }
            setPipelineBusy(false);
            if (next.status === "done") {
              toast("處理完成", "success");
              reload();
            } else {
              toast(`處理失敗：${next.error ?? "unknown error"}`, "error");
            }
          }
        } catch (err) {
          // poll error — leave interval running
          console.warn("poll job failed", err);
        }
      }, 2000);
    } catch (err) {
      setPipelineBusy(false);
      toast(`建立處理 job 失敗：${String(err)}`, "error");
    }
  }

  async function applyAdjustment(photoIds: string[]) {
    if (photoIds.length === 0) return;
    setAdjustmentBusy(true);
    try {
      if (photoIds.length === 1) {
        await api.applyAdjustment(photoIds[0], adjustmentParams);
        toast("已套用微調", "success");
        reload();
        setAdjustmentBusy(false);
        return;
      }
      if (!projectId) {
        setAdjustmentBusy(false);
        return;
      }
      const created = await api.createAdjustmentJob(projectId, adjustmentParams, photoIds);
      setAdjustmentJob(created);
      toast(`已開始套用微調，共 ${created.total} 張`, "info");
      if (adjustmentPollRef.current !== null) {
        window.clearInterval(adjustmentPollRef.current);
      }
      adjustmentPollRef.current = window.setInterval(async () => {
        try {
          const next = await api.getAdjustmentJob(created.id);
          setAdjustmentJob(next);
          if (next.status === "done" || next.status === "failed") {
            if (adjustmentPollRef.current !== null) {
              window.clearInterval(adjustmentPollRef.current);
              adjustmentPollRef.current = null;
            }
            setAdjustmentBusy(false);
            if (next.status === "done") {
              toast("批次微調完成", "success");
              reload();
            } else {
              toast(`批次微調失敗：${next.error ?? "unknown error"}`, "error");
            }
          }
        } catch (err) {
          console.warn("poll adjustment job failed", err);
        }
      }, 1500);
    } catch (err) {
      toast(`套用微調失敗：${String(err)}`, "error");
      setAdjustmentBusy(false);
    }
  }

  function rotateActivePhoto(direction: "left" | "right") {
    if (!activePhotoId) return;
    const current = adjustmentParamsRef.current;
    const delta = direction === "right" ? 90 : 270;
    const next = {
      ...current,
      orientation: (current.orientation + delta) % 360,
    };
    updateAdjustmentParams(next);
  }

  async function savePreset(name: string) {
    try {
      await api.createAdjustmentPreset(name, adjustmentParams, projectId);
      toast("已儲存 preset", "success");
      reloadPresets();
    } catch (err) {
      toast(`儲存 preset 失敗：${String(err)}`, "error");
    }
  }

  async function deletePreset(preset: AdjustmentPreset) {
    try {
      await api.deleteAdjustmentPreset(preset.id);
      toast(`已刪除 preset：${preset.name}`, "success");
      reloadPresets();
    } catch (err) {
      toast(`刪除 preset 失敗：${String(err)}`, "error");
    }
  }

  if (!projectId) {
    return (
      <main className="page page--narrow preview-empty">
        <section className="hero">
          <div className="hero__kicker">預覽</div>
          <h1 className="hero__title">
            還沒選<em>專案</em>。
          </h1>
          <p className="hero__lede">從上傳頁建立或選一個既有專案。</p>
        </section>
        <Link to="/upload" className="cta cta--primary">
          ← 回到上傳頁
        </Link>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page preview">
        <section className="hero">
          <div className="hero__kicker">預覽 · 錯誤</div>
          <h1 className="hero__title">
            讀不到<em>專案</em>。
          </h1>
        </section>
        <div className="alert" role="alert">
          {error}
        </div>
        <Link to="/upload" className="cta cta--quiet preview__back">
          ← 回到上傳頁
        </Link>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="page preview">
        <section className="hero">
          <div className="hero__kicker">預覽</div>
          <h1 className="hero__title">載入中…</h1>
        </section>
        <Spinner label="正在讀取專案" />
      </main>
    );
  }

  const activePhoto = project.photos.find((p) => p.id === activePhotoId) ?? null;
  const samplePhoto =
    activePhoto ??
    project.photos.find((p) => Object.keys(p.processed_paths ?? {}).length > 0) ??
    null;
  const processedKeys = samplePhoto ? Object.keys(samplePhoto.processed_paths ?? {}) : [];
  const samplePreset = processedKeys[0] ? (processedKeys[0] as ColorGradePreset | "adjusted") : null;
  const basePreset = processedKeys.find((key) => key !== "adjusted") as
    | ColorGradePreset
    | undefined;
  const activePreviewUrl =
    preview && preview.photoId === samplePhoto?.id ? preview.url : null;
  const activeBasePreviewUrl =
    basePreview && basePreview.photoId === samplePhoto?.id ? basePreview.url : null;
  const baseDisplayUrl =
    samplePhoto && basePreset
      ? api.processedPhotoUrl(samplePhoto.id, basePreset)
      : samplePhoto
        ? api.photoFileUrl(samplePhoto.id)
        : "";
  const progressPct =
    job && job.total > 0 ? Math.round((job.progress / job.total) * 100) : 0;
  const adjustmentProgressPct =
    adjustmentJob && adjustmentJob.total > 0
      ? Math.round((adjustmentJob.progress / adjustmentJob.total) * 100)
      : 0;

  return (
    <main className="page preview">
      <section className="hero preview__hero">
        <div className="hero__kicker">
          預覽 · 專案 #{String(project.id).slice(0, 8)}
        </div>
        <h1 className="hero__title">{project.name}</h1>
        <p className="hero__lede">{project.photo_count} 張照片</p>
      </section>

      <PipelinePanel
        selectedCount={selected.size}
        totalCount={project.photos.length}
        busy={pipelineBusy}
        onSubmit={handleSubmit}
      />

      {job && (
        <section className="job-status">
          <header className="job-status__head">
            <span className="mono">job #{job.id.slice(0, 8)}</span>
            <span className={`job-status__pill job-status__pill--${job.status}`}>
              {job.status}
            </span>
          </header>
          <div className="job-status__bar" aria-hidden>
            <div
              className="job-status__bar-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <p className="job-status__meta mono">
            {job.progress} / {job.total} 完成
            {job.error ? ` · ${job.error}` : ""}
          </p>
          <ol className="job-status__queue">
            {job.photo_ids.map((pid, idx) => {
              const photo = project.photos.find((p) => p.id === pid);
              const name = photo?.original_filename ?? pid.slice(0, 8);
              let state: "done" | "running" | "queued" = "queued";
              if (job.status === "done") state = "done";
              else if (idx < job.progress) state = "done";
              else if (idx === job.progress && job.status === "running")
                state = "running";
              const icon = state === "done" ? "✓" : state === "running" ? "●" : "○";
              return (
                <li key={pid} className={`job-status__queue-item job-status__queue-item--${state}`}>
                  <span className="job-status__queue-icon" aria-hidden>{icon}</span>
                  <span className="job-status__queue-idx mono">
                    {String(idx + 1).padStart(String(job.total).length, "0")}/{job.total}
                  </span>
                  <span className="job-status__queue-name" title={name}>{name}</span>
                  <span className="job-status__queue-state mono">{state === "running" ? "處理中" : state === "done" ? "完成" : "等待中"}</span>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {samplePhoto && (
        <section className="section">
          <header className="section__head">
            <h2 className="section__title">前後對比</h2>
            <span className="section__meta mono">
              {activePreviewUrl ? "manual_adjust" : samplePreset ?? "original"}
            </span>
          </header>
          <BeforeAfter
            key={`${samplePhoto.id}:${adjustmentParams.orientation}:${samplePreset ?? "original"}`}
            beforeUrl={activeBasePreviewUrl ?? baseDisplayUrl}
            afterUrl={
              activePreviewUrl ??
              (samplePreset
                ? api.processedPhotoUrl(samplePhoto.id, samplePreset)
                : api.photoFileUrl(samplePhoto.id))
            }
            alt={samplePhoto.original_filename}
          />
        </section>
      )}

      {adjustmentJob && (
        <section className="job-status">
          <header className="job-status__head">
            <span className="mono">adjust #{adjustmentJob.id.slice(0, 8)}</span>
            <span className={`job-status__pill job-status__pill--${adjustmentJob.status}`}>
              {adjustmentJob.status}
            </span>
          </header>
          <div className="job-status__bar" aria-hidden>
            <div
              className="job-status__bar-fill"
              style={{ width: `${adjustmentProgressPct}%` }}
            />
          </div>
          <p className="job-status__meta mono">
            {adjustmentJob.progress} / {adjustmentJob.total} 微調完成
            {adjustmentJob.error ? ` · ${adjustmentJob.error}` : ""}
          </p>
        </section>
      )}

      {activePhotoId && (
        <AdjustmentPanel
          params={adjustmentParams}
          presets={presets}
          geometryBaseUrl={activeBasePreviewUrl ?? baseDisplayUrl}
          geometryPreviewUrl={activePreviewUrl ?? activeBasePreviewUrl ?? baseDisplayUrl}
          busy={adjustmentBusy}
          onChange={updateAdjustmentParams}
          onApplyCurrent={() => void applyAdjustment([activePhotoId])}
          onApplySelected={() => void applyAdjustment(Array.from(selected))}
          onReset={() => updateAdjustmentParams(structuredClone(DEFAULT_ADJUSTMENT_PARAMS))}
          onSavePreset={(name) => void savePreset(name)}
          onLoadPreset={(preset) => updateAdjustmentParams(preset.params)}
          onDeletePreset={(preset) => void deletePreset(preset)}
          onRotateLeft={() => rotateActivePhoto("left")}
          onRotateRight={() => rotateActivePhoto("right")}
        />
      )}

      <section className="section">
        <header className="section__head">
          <h2 className="section__title">照片清單</h2>
          <span className="section__meta">
            {selected.size} / {project.photos.length} 已選
          </span>
        </header>

        <div className="bulk-bar">
          <div className="bulk-bar__group">
            <button
              type="button"
              className="bulk-bar__btn"
              onClick={selectAll}
              disabled={selected.size === project.photos.length}
            >
              全選
            </button>
            <button
              type="button"
              className="bulk-bar__btn"
              onClick={selectAdjusted}
            >
              只選已調整
            </button>
            <button
              type="button"
              className="bulk-bar__btn"
              onClick={selectNone}
              disabled={selected.size === 0}
            >
              取消全選
            </button>
          </div>
          <div className="bulk-bar__group">
            <Link to={`/export/${project.id}`} className="cta cta--primary">
              匯出 zip →
            </Link>
          </div>
        </div>

        <PhotoGrid
          photos={project.photos}
          selectable
          selectedIds={selected}
          activeId={samplePhoto?.id ?? activePhotoId}
          onToggleSelect={toggle}
          onOpenPreview={setActivePhotoId}
        />
      </section>
    </main>
  );
}
