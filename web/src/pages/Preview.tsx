import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { BeforeAfter } from "@/components/BeforeAfter";
import { PhotoGrid } from "@/components/PhotoGrid";
import { PipelinePanel } from "@/components/PipelinePanel";
import { Spinner } from "@/components/Spinner";
import { useToast } from "@/components/Toast";
import type {
  ColorGradePreset,
  ProcessingJob,
  ProcessingJobCreate,
  ProjectDetail,
} from "@/types";

import "./Preview.css";

export default function PreviewPage() {
  const { projectId } = useParams();
  const { push: toast } = useToast();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<number | null>(null);

  function reload() {
    if (!projectId) return;
    api
      .getProject(projectId)
      .then((p) => setProject(p))
      .catch((err) => setError(String(err)));
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
        setSelected(new Set(p.photos.map((ph) => ph.id)));
      })
      .catch((err) => setError(String(err)));
  }, [projectId]);

  useEffect(() => {
    return () => {
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
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

  function selectNone() {
    setSelected(new Set());
  }

  async function handleSubmit(payload: ProcessingJobCreate) {
    if (!projectId || !project) return;
    setBusy(true);
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
            setBusy(false);
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
      setBusy(false);
      toast(`建立處理 job 失敗：${String(err)}`, "error");
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

  const samplePhoto =
    project.photos.find((p) => Object.keys(p.processed_paths ?? {}).length > 0) ??
    null;
  const samplePreset =
    samplePhoto && Object.keys(samplePhoto.processed_paths)[0]
      ? (Object.keys(samplePhoto.processed_paths)[0] as ColorGradePreset)
      : null;
  const progressPct =
    job && job.total > 0 ? Math.round((job.progress / job.total) * 100) : 0;

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
        busy={busy}
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

      {samplePhoto && samplePreset && (
        <section className="section">
          <header className="section__head">
            <h2 className="section__title">前後對比</h2>
            <span className="section__meta mono">{samplePreset}</span>
          </header>
          <BeforeAfter
            beforeUrl={api.photoFileUrl(samplePhoto.id)}
            afterUrl={api.processedPhotoUrl(samplePhoto.id, samplePreset)}
            alt={samplePhoto.original_filename}
          />
        </section>
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
          onToggleSelect={toggle}
        />
      </section>
    </main>
  );
}
