import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { Dropzone } from "@/components/Dropzone";
import { Spinner } from "@/components/Spinner";
import { StylePicker } from "@/components/StylePicker";
import type { StylePreset } from "@/components/StylePicker";
import { useToast } from "@/components/Toast";
import type { Project } from "@/types";

import "./Upload.css";

const DEFAULT_STYLE: StylePreset = "showroom_white";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatCreatedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`;
}

interface PendingPhoto {
  id: string;
  file: File;
  previewUrl: string;
}

export default function UploadPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [pending, setPending] = useState<PendingPhoto[]>([]);
  const [style, setStyle] = useState<StylePreset>(DEFAULT_STYLE);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((err) => setProjectsError(String(err)));
  }, []);

  // Object URLs leak unless we revoke them when the pending list churns.
  useEffect(() => {
    return () => {
      pending.forEach((p) => URL.revokeObjectURL(p.previewUrl));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totalBytes = useMemo(
    () => pending.reduce((sum, p) => sum + p.file.size, 0),
    [pending],
  );

  function addFiles(files: File[]) {
    const fresh = files.map<PendingPhoto>((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
      file,
      previewUrl: URL.createObjectURL(file),
    }));
    setPending((prev) => [...prev, ...fresh]);
    setError(null);
  }

  function removePending(id: string) {
    setPending((prev) => {
      const next = prev.filter((p) => {
        if (p.id === id) {
          URL.revokeObjectURL(p.previewUrl);
          return false;
        }
        return true;
      });
      return next;
    });
  }

  function clearPending() {
    pending.forEach((p) => URL.revokeObjectURL(p.previewUrl));
    setPending([]);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) {
      setError("請輸入專案名稱。");
      return;
    }
    if (pending.length === 0) {
      setError("請至少選擇一張照片。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const project = await api.createProject(name.trim());
      await api.uploadPhotos(
        project.id,
        pending.map((p) => p.file),
      );
      // Persist the picked style for v0.2 — backend ignores for now.
      try {
        window.localStorage.setItem(
          `frame-processor:style:${project.id}`,
          style,
        );
      } catch {
        /* private mode / quota: not fatal */
      }
      toast.push(`已建立專案「${project.name}」並上傳 ${pending.length} 張`, "success");
      clearPending();
      navigate(`/preview/${project.id}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      toast.push(`上傳失敗：${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page upload">
      <section className="hero">
        <div className="hero__kicker">上傳 · 新增專案</div>
        <h1 className="hero__title">
          一次上傳一批，<em>整批</em>套用同一個風格。
        </h1>
        <p className="hero__lede">
          給專案一個名字，丟進照片，挑一個色調預設。原圖永遠保留，處理結果會另存。
        </p>
      </section>

      <form onSubmit={handleSubmit} className="upload-form">
        <section className="section upload-form__name">
          <header className="section__head">
            <h2 className="section__title">專案名稱</h2>
            <span className="section__meta">{name.length} / 120</span>
          </header>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例：BMW M3 2026-05-07 outdoor"
            maxLength={120}
            className="upload-form__input"
            disabled={busy}
          />
        </section>

        <section className="section">
          <header className="section__head">
            <h2 className="section__title">照片</h2>
            <span className="section__meta">
              {pending.length} 張 · {formatBytes(totalBytes)}
            </span>
          </header>
          <Dropzone onPick={addFiles} disabled={busy} />

          {pending.length > 0 && (
            <>
              <div className="thumb-grid">
                {pending.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="thumb"
                    onClick={() => removePending(p.id)}
                    title="移除這張"
                    disabled={busy}
                  >
                    <img src={p.previewUrl} alt={p.file.name} loading="lazy" />
                    <span className="thumb__overlay">
                      <span className="thumb__name">{p.file.name}</span>
                      <span className="thumb__meta mono">
                        {formatBytes(p.file.size)}
                      </span>
                    </span>
                    <span className="thumb__remove" aria-hidden>
                      ×
                    </span>
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="upload-form__clear"
                onClick={clearPending}
                disabled={busy}
              >
                清空清單
              </button>
            </>
          )}
        </section>

        <section className="section">
          <header className="section__head">
            <h2 className="section__title">色調風格</h2>
            <span className="section__meta">處理參數可在預覽頁調整</span>
          </header>
          <StylePicker value={style} onChange={setStyle} />
          <p className="upload-form__hint">
            這裡先記下偏好的色調；上傳完到預覽頁再決定要不要套水平校正、選裁剪比例，再一鍵送整批進 worker 後製。
          </p>
        </section>

        <section className="section upload-form__actions">
          {error ? (
            <div className="alert" role="alert">
              {error}
            </div>
          ) : null}
          <div className="upload-form__cta-row">
            <Link to="/preview" className="cta cta--quiet">
              ← 看既有專案
            </Link>
            <button
              type="submit"
              className="cta cta--primary"
              disabled={busy || pending.length === 0 || !name.trim()}
            >
              {busy ? (
                <Spinner label="上傳中" />
              ) : (
                `建立並上傳 ${pending.length} 張 →`
              )}
            </button>
          </div>
        </section>
      </form>

      <section className="section recent">
        <header className="section__head">
          <h2 className="section__title">既有專案</h2>
          <span className="section__meta">
            {projects ? `${projects.length} 件` : "載入中…"}
          </span>
        </header>

        {projectsError ? (
          <div className="alert" role="alert">
            專案載入失敗 · {projectsError}
          </div>
        ) : null}

        {projects === null && !projectsError ? (
          <div className="recent__empty">
            <Spinner label="載入中" />
          </div>
        ) : projects && projects.length === 0 ? (
          <div className="recent__empty">
            <p className="mono">尚無專案 — 從上方建立第一個。</p>
          </div>
        ) : projects ? (
          <ol className="recent__list">
            {projects.map((p) => (
              <li key={p.id} className="recent__item">
                <div className="recent__main">
                  <h3 className="recent__name">{p.name}</h3>
                  <div className="recent__meta mono">
                    {p.photo_count} 張 · {formatCreatedAt(p.created_at)}
                  </div>
                </div>
                <div className="recent__actions">
                  <Link
                    to={`/preview/${p.id}`}
                    className="cta cta--quiet"
                  >
                    預覽
                  </Link>
                  <Link
                    to={`/export/${p.id}`}
                    className="cta cta--quiet"
                  >
                    匯出
                  </Link>
                </div>
              </li>
            ))}
          </ol>
        ) : null}
      </section>
    </main>
  );
}
