import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { Spinner } from "@/components/Spinner";
import { useToast } from "@/components/Toast";
import type { Export, ExportStatus, ProjectDetail } from "@/types";
import { formatServiceTime } from "@/utils/time";
import { formatAIVersionLabel, jobStatusLabel } from "@/utils/processingVersionLabel";

import "./Export.css";

const STATUS_LABEL: Record<ExportStatus, string> = {
  pending: "排隊中",
  running: "打包中",
  done: "已完成",
  failed: "失敗",
};


export default function ExportPage() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const toast = useToast();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [exportRow, setExportRow] = useState<Export | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedProcessingJobId, setSelectedProcessingJobId] = useState<string>("");
  const [allowPartial, setAllowPartial] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    const requestedJobId = searchParams.get("processing_job_id") ?? "";
    api
      .getProject(projectId)
      .then((next) => {
        setProject(next);
        if (requestedJobId && next.processing_versions.some((version) => version.id === requestedJobId)) {
          setSelectedProcessingJobId(requestedJobId);
        }
      })
      .catch((err) => setError(String(err)));
  }, [projectId, searchParams]);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
      }
    };
  }, []);

  function pollUntilDone(exportId: string) {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const fresh = await api.getExport(exportId);
        setExportRow(fresh);
        if (fresh.status === "done" || fresh.status === "failed") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          if (fresh.status === "done") {
            toast.push("zip 打包完成，可以下載了。", "success");
          } else if (fresh.status === "failed") {
            toast.push(`打包失敗：${fresh.error ?? "未知錯誤"}`, "error");
          }
        }
      } catch (err) {
        setError(String(err));
        if (pollRef.current) window.clearInterval(pollRef.current);
      }
    }, 1500);
  }

  async function startExport() {
    if (!projectId) return;
    setError(null);
    setBusy(true);
    try {
      const created = await api.createExport(projectId, {
        processing_job_id: selectedProcessingJobId || null,
        allow_partial: allowPartial,
      });
      setExportRow(created);
      toast.push("已送出打包任務，等 worker 完成。", "info");
      pollUntilDone(created.id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      toast.push(`觸發打包失敗：${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  if (!projectId) {
    return (
      <main className="page page--narrow export-empty">
        <section className="hero">
          <div className="hero__kicker">匯出</div>
          <h1 className="hero__title">
            還沒選<em>專案</em>。
          </h1>
          <p className="hero__lede">
            匯出會把整個專案的照片打包成一個 zip，目前只包原圖，v0.6 之後會包處理結果。
          </p>
        </section>
        <Link to="/upload" className="cta cta--primary">
          ← 回到上傳頁
        </Link>
      </main>
    );
  }

  const inProgress =
    exportRow?.status === "pending" || exportRow?.status === "running";
  const status = exportRow?.status ?? null;

  return (
    <main className="page export">
      <section className="hero">
        <div className="hero__kicker">匯出 · 打包 zip</div>
        <h1 className="hero__title">
          {project ? project.name : "讀取中"}
        </h1>
        {project ? (
          <p className="hero__lede">
            {project.photo_count} 張照片 · 點下方按鈕讓 worker 把整個資料夾打包成 zip。
          </p>
        ) : null}
      </section>

      {error ? (
        <div className="alert" role="alert">
          {error}
        </div>
      ) : null}

      <section className="section export-card">
        <header className="section__head">
          <h2 className="section__title">打包狀態</h2>
          {status ? (
            <span className="section__meta">
              <span
                className={`dot ${
                  status === "done"
                    ? "dot--up"
                    : status === "failed"
                      ? "dot--down"
                      : "dot--processing"
                }`}
              />
              {STATUS_LABEL[status]}
            </span>
          ) : (
            <span className="section__meta">尚未開始</span>
          )}
        </header>

        <div className="export-card__body">
          {project ? (
            <div className="export-card__options">
              <label>
                <span>匯出來源</span>
                <select
                  value={selectedProcessingJobId}
                  onChange={(event) => setSelectedProcessingJobId(event.target.value)}
                >
                  <option value="">最新可用版本（手動微調優先）</option>
                  {project.processing_versions.map((version) => (
                    <option key={version.id} value={version.id}>
                      {formatAIVersionLabel(version)} · {jobStatusLabel(version.status)}
                    </option>
                  ))}
                </select>
              </label>
              {selectedProcessingJobId ? (
                <label className="export-card__check">
                  <input
                    type="checkbox"
                    checked={allowPartial}
                    onChange={(event) => setAllowPartial(event.target.checked)}
                  />
                  <span>若此 AI 版本有缺圖，仍匯出已完成照片</span>
                </label>
              ) : null}
            </div>
          ) : null}

          {!exportRow ? (
            <p className="export-card__hint">
              還沒打包過。建立 zip 之後 worker 會在背景處理；視照片數量約幾秒到幾十秒。
            </p>
          ) : (
            <dl className="export-card__detail mono">
              <div>
                <dt>建立時間</dt>
                <dd>{formatServiceTime(exportRow.created_at)}</dd>
              </div>
              <div>
                <dt>完成時間</dt>
                <dd>{formatServiceTime(exportRow.completed_at)}</dd>
              </div>
              <div>
                <dt>狀態</dt>
                <dd>{STATUS_LABEL[exportRow.status]}</dd>
              </div>
            </dl>
          )}

          {inProgress ? (
            <div className="progress-track" aria-hidden>
              <div className="progress-bar progress-bar--indeterminate" />
            </div>
          ) : null}

          {exportRow?.error ? (
            <div className="alert" role="alert">
              {exportRow.error}
            </div>
          ) : null}
        </div>

        <div className="export-card__cta">
          <button
            type="button"
            className="cta cta--primary"
            onClick={startExport}
            disabled={inProgress || busy}
          >
            {busy ? (
              <Spinner label="送出中" />
            ) : inProgress ? (
              `${STATUS_LABEL[status as ExportStatus]}…`
            ) : exportRow?.status === "done" ? (
              "重新打包"
            ) : (
              "建立 zip →"
            )}
          </button>

          {exportRow?.status === "done" ? (
            <a
              href={api.exportDownloadUrl(exportRow.id)}
              className="cta cta--quiet export-card__download"
            >
              下載 zip ↓
            </a>
          ) : null}

          <Link to={`/preview/${projectId}`} className="cta cta--quiet">
            ← 回到預覽
          </Link>
        </div>
      </section>
    </main>
  );
}
