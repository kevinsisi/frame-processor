import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { BeforeAfter } from "@/components/BeforeAfter";
import { ProcessingProgress } from "@/components/ProcessingProgress";
import { Spinner } from "@/components/Spinner";
import { StylePicker } from "@/components/StylePicker";
import type { StylePreset } from "@/components/StylePicker";
import { useToast } from "@/components/Toast";
import type {
  AutoCropAspect,
  Photo,
  ProcessingJob,
  ProjectDetail,
} from "@/types";

import "./Preview.css";

const STYLE_LABEL: Record<StylePreset, string> = {
  showroom_white: "展示間白",
  outdoor_warm: "戶外暖調",
  night_cold: "夜拍冷調",
};

const STYLE_VALUES: StylePreset[] = ["showroom_white", "outdoor_warm", "night_cold"];

const POLL_MS = 1500;
const STYLE_KEY_PREFIX = "frame-processor:style:";
const ASPECT_KEY_PREFIX = "frame-processor:aspect:";
const LEVEL_KEY_PREFIX = "frame-processor:level:";

function readSavedStyle(projectId: string): StylePreset {
  try {
    const v = window.localStorage.getItem(`${STYLE_KEY_PREFIX}${projectId}`);
    if (STYLE_VALUES.includes(v as StylePreset)) return v as StylePreset;
  } catch {
    /* ignore */
  }
  return "showroom_white";
}

function readSavedAspect(projectId: string): AutoCropAspect {
  try {
    const v = window.localStorage.getItem(`${ASPECT_KEY_PREFIX}${projectId}`);
    const allowed: AutoCropAspect[] = ["original", "3:2", "4:3", "16:9", "1:1", "9:16"];
    if (allowed.includes(v as AutoCropAspect)) return v as AutoCropAspect;
  } catch {
    /* ignore */
  }
  return "original";
}

function readSavedLevel(projectId: string): boolean {
  try {
    const v = window.localStorage.getItem(`${LEVEL_KEY_PREFIX}${projectId}`);
    if (v === "0") return false;
    if (v === "1") return true;
  } catch {
    /* ignore */
  }
  return true;
}

export default function PreviewPage() {
  const { projectId } = useParams();
  const toast = useToast();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [style, setStyle] = useState<StylePreset>("showroom_white");
  const [aspect, setAspect] = useState<AutoCropAspect>("original");
  const [levelCorrect, setLevelCorrect] = useState<boolean>(true);
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [activePhotoId, setActivePhotoId] = useState<string | null>(null);
  const pollTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    setStyle(readSavedStyle(projectId));
    setAspect(readSavedAspect(projectId));
    setLevelCorrect(readSavedLevel(projectId));
    setProject(null);
    setError(null);
    api
      .getProject(projectId)
      .then((p) => {
        setProject(p);
        setSelected(new Set(p.photos.map((ph) => ph.id)));
        setActivePhotoId(p.photos[0]?.id ?? null);
      })
      .catch((err) => setError(String(err)));
  }, [projectId]);

  // Persist preset / aspect / level toggle so 跨頁切換不會回到預設值
  useEffect(() => {
    if (!projectId) return;
    try {
      window.localStorage.setItem(`${STYLE_KEY_PREFIX}${projectId}`, style);
      window.localStorage.setItem(`${ASPECT_KEY_PREFIX}${projectId}`, aspect);
      window.localStorage.setItem(
        `${LEVEL_KEY_PREFIX}${projectId}`,
        levelCorrect ? "1" : "0",
      );
    } catch {
      /* ignore */
    }
  }, [projectId, style, aspect, levelCorrect]);

  const refreshProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const fresh = await api.getProject(projectId);
      setProject(fresh);
    } catch (err) {
      // 不洗掉現有 state；下次 poll 會重試
      console.error(err);
    }
  }, [projectId]);

  const stopPolling = useCallback(() => {
    if (pollTimer.current !== null) {
      window.clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const pollOnce = useCallback(
    async (jobId: string) => {
      try {
        const fresh = await api.getProcessing(jobId);
        setJob(fresh);
        if (fresh.status === "done" || fresh.status === "failed") {
          stopPolling();
          await refreshProject();
          if (fresh.status === "done") {
            toast.push(`處理完成：${fresh.progress_done} 張`, "success");
          } else {
            toast.push("處理失敗，請看詳細訊息", "error");
          }
        } else {
          pollTimer.current = window.setTimeout(() => pollOnce(jobId), POLL_MS);
        }
      } catch (err) {
        console.error(err);
        pollTimer.current = window.setTimeout(() => pollOnce(jobId), POLL_MS);
      }
    },
    [refreshProject, stopPolling, toast],
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  function toggle(photoId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(photoId)) next.delete(photoId);
      else next.add(photoId);
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

  async function startProcessing() {
    if (!project) return;
    if (selected.size === 0) {
      toast.push("請先選照片再開始處理", "error");
      return;
    }
    setBusy(true);
    setJob(null);
    try {
      const photoIds =
        selected.size === project.photos.length
          ? []
          : Array.from(selected);
      const created = await api.createProcessing(project.id, {
        preset: style,
        photo_ids: photoIds,
        level_correct: levelCorrect,
        auto_crop_aspect: aspect,
      });
      setJob(created);
      pollTimer.current = window.setTimeout(() => pollOnce(created.id), POLL_MS);
      toast.push(
        `已送出 ${created.progress_total} 張，套用「${STYLE_LABEL[style]}」`,
        "success",
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.push(`送出失敗：${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  const activePhoto: Photo | null = useMemo(() => {
    if (!project || !activePhotoId) return null;
    return project.photos.find((p) => p.id === activePhotoId) ?? null;
  }, [project, activePhotoId]);

  const activeProcessedUrl = useMemo(() => {
    if (!activePhoto) return null;
    if (!activePhoto.processed_paths?.[style]) return null;
    return api.processedPhotoUrl(activePhoto.id, style);
  }, [activePhoto, style]);

  const processedCount = useMemo(() => {
    if (!project) return 0;
    return project.photos.filter((p) => Boolean(p.processed_paths?.[style])).length;
  }, [project, style]);

  if (!projectId) {
    return (
      <main className="page page--narrow preview-empty">
        <section className="hero">
          <div className="hero__kicker">預覽</div>
          <h1 className="hero__title">
            還沒選<em>專案</em>。
          </h1>
          <p className="hero__lede">
            從上傳頁建立或選一個既有專案，這裡會顯示原圖與處理結果。
          </p>
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

  return (
    <main className="page preview">
      <section className="hero preview__hero">
        <div className="hero__kicker">
          預覽 · 專案 #{String(project.id).slice(0, 8)}
        </div>
        <h1 className="hero__title">{project.name}</h1>
        <p className="hero__lede">
          {project.photo_count} 張原圖
          <span className="preview__hero-sep" aria-hidden>
            ／
          </span>
          目前色調：<em>{STYLE_LABEL[style]}</em>
          <span className="preview__hero-sep" aria-hidden>
            ／
          </span>
          已處理 {processedCount} / {project.photo_count}
        </p>
      </section>

      <section className="section">
        <header className="section__head">
          <h2 className="section__title">色調風格 · 處理參數</h2>
          <span className="section__meta">v0.2 — Pillow + Hough + 能量裁剪</span>
        </header>
        <StylePicker
          value={style}
          onChange={setStyle}
          levelCorrect={levelCorrect}
          onLevelCorrectChange={setLevelCorrect}
          aspect={aspect}
          onAspectChange={setAspect}
          disabled={busy || job?.status === "running" || job?.status === "pending"}
          showOptions
        />
      </section>

      {job ? (
        <section className="section">
          <header className="section__head">
            <h2 className="section__title">處理進度</h2>
            <span className="section__meta mono">
              {STYLE_LABEL[job.preset]} · {job.auto_crop_aspect}
              {job.level_correct ? " · 水平校正" : ""}
            </span>
          </header>
          <ProcessingProgress job={job} />
        </section>
      ) : null}

      {activePhoto ? (
        <section className="section">
          <header className="section__head">
            <h2 className="section__title">對比預覽</h2>
            <span className="section__meta mono">
              {activePhoto.original_filename}
            </span>
          </header>
          {activeProcessedUrl ? (
            <BeforeAfter
              alt={activePhoto.original_filename}
              beforeUrl={api.photoFileUrl(activePhoto.id)}
              afterUrl={activeProcessedUrl}
              afterLabel={STYLE_LABEL[style]}
            />
          ) : (
            <div className="preview__no-processed">
              <p className="mono">
                這張照片在「{STYLE_LABEL[style]}」還沒有處理結果。
              </p>
              <p className="preview__hint">
                選好參數 → 點下方「開始處理」即可送出整批；完成後此處會顯示原圖↔處理後拖拉條。
              </p>
            </div>
          )}
        </section>
      ) : null}

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
            <button
              type="button"
              className="cta cta--primary"
              onClick={startProcessing}
              disabled={
                busy ||
                selected.size === 0 ||
                job?.status === "running" ||
                job?.status === "pending"
              }
            >
              {busy
                ? "送出中…"
                : job?.status === "running" || job?.status === "pending"
                ? "處理中…"
                : `開始處理 ${selected.size} 張`}
            </button>
            <Link to={`/export/${project.id}`} className="cta cta--quiet">
              匯出 zip →
            </Link>
          </div>
        </div>

        <ul className="preview-grid">
          {project.photos.map((photo) => {
            const isActive = activePhotoId === photo.id;
            const isSelected = selected.has(photo.id);
            const hasProcessed = Boolean(photo.processed_paths?.[style]);
            const thumbUrl = hasProcessed
              ? api.processedPhotoUrl(photo.id, style)
              : api.thumbnailUrl(photo.id);
            return (
              <li
                key={photo.id}
                className={`preview-tile${isActive ? " preview-tile--active" : ""}${
                  isSelected ? " preview-tile--selected" : ""
                }`}
              >
                <button
                  type="button"
                  className="preview-tile__thumb"
                  onClick={() => setActivePhotoId(photo.id)}
                  title={photo.original_filename}
                >
                  <img
                    src={thumbUrl}
                    alt={photo.original_filename}
                    loading="lazy"
                  />
                  {hasProcessed ? (
                    <span className="preview-tile__badge mono">已處理</span>
                  ) : null}
                </button>
                <div className="preview-tile__row">
                  <label className="preview-tile__select">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggle(photo.id)}
                    />
                    <span className="mono">
                      {photo.original_filename}
                    </span>
                  </label>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </main>
  );
}
