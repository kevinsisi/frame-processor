import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { PhotoGrid } from "@/components/PhotoGrid";
import { Spinner } from "@/components/Spinner";
import type { StylePreset } from "@/components/StylePicker";
import type { ProjectDetail } from "@/types";

import "./Preview.css";

const STYLE_LABEL: Record<StylePreset, string> = {
  showroom_white: "展示間白",
  outdoor_warm: "戶外暖調",
  night_cold: "夜拍冷調",
};

function readSavedStyle(projectId: string): StylePreset | null {
  try {
    const v = window.localStorage.getItem(`frame-processor:style:${projectId}`);
    if (v === "showroom_white" || v === "outdoor_warm" || v === "night_cold") {
      return v;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export default function PreviewPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

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

  const savedStyle = useMemo(
    () => (projectId ? readSavedStyle(projectId) : null),
    [projectId],
  );

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

  if (!projectId) {
    return (
      <main className="page page--narrow preview-empty">
        <section className="hero">
          <div className="hero__kicker">預覽</div>
          <h1 className="hero__title">
            還沒選<em>專案</em>。
          </h1>
          <p className="hero__lede">
            從上傳頁建立或選一個既有專案，這裡會顯示原圖與處理結果（v0.2 之後）。
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
          {project.photo_count} 張照片
          {savedStyle ? (
            <>
              <span className="preview__hero-sep" aria-hidden>
                ／
              </span>
              色調預設：<em>{STYLE_LABEL[savedStyle]}</em>
            </>
          ) : null}
        </p>
        <p className="preview__hero-note mono">
          v0.1 walking skeleton — 目前顯示原圖。處理後的 before/after 對比會在 v0.2 上線。
        </p>
      </section>

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
            <span
              className="cta cta--quiet"
              aria-disabled="true"
              title="批次處理會在 v0.2 上線"
            >
              批次套用色調 · v0.2
            </span>
            <Link
              to={`/export/${project.id}`}
              className="cta cta--primary"
            >
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
