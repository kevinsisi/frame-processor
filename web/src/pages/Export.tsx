import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/Card";
import type { Export, ProjectDetail } from "@/types";

export default function ExportPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [exportRow, setExportRow] = useState<Export | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    api.getProject(projectId).then(setProject).catch((err) => setError(String(err)));
  }, [projectId]);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
      }
    };
  }, []);

  async function startExport() {
    if (!projectId) return;
    setError(null);
    try {
      const created = await api.createExport(projectId);
      setExportRow(created);
      pollUntilDone(created.id);
    } catch (err) {
      setError(String(err));
    }
  }

  function pollUntilDone(exportId: string) {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const fresh = await api.getExport(exportId);
        setExportRow(fresh);
        if (fresh.status === "done" || fresh.status === "failed") {
          if (pollRef.current) window.clearInterval(pollRef.current);
        }
      } catch (err) {
        setError(String(err));
      }
    }, 1500);
  }

  if (!projectId) {
    return (
      <Card title="匯出">
        <div className="text-sm text-slate-500">
          請從 <Link to="/upload" className="text-brand underline">上傳頁</Link> 選擇一個既有專案。
        </div>
      </Card>
    );
  }

  return (
    <Card title="匯出 zip">
      {error ? <div className="mb-3 text-sm text-red-600">{error}</div> : null}
      {project ? (
        <div className="mb-4 text-sm text-slate-700">
          專案：<span className="font-medium">{project.name}</span>（{project.photo_count} 張）
        </div>
      ) : null}
      <button
        onClick={startExport}
        disabled={exportRow?.status === "pending" || exportRow?.status === "running"}
        className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {exportRow?.status === "pending" || exportRow?.status === "running"
          ? `打包中…（${exportRow.status}）`
          : "建立 zip"}
      </button>

      {exportRow ? (
        <div className="mt-4 text-sm space-y-1">
          <div>
            狀態：<span className="font-medium">{exportRow.status}</span>
          </div>
          {exportRow.error ? (
            <div className="text-red-600">錯誤：{exportRow.error}</div>
          ) : null}
          {exportRow.status === "done" ? (
            <a
              href={api.exportDownloadUrl(exportRow.id)}
              className="inline-block mt-2 rounded-md border border-brand px-4 py-2 text-sm font-medium text-brand hover:bg-brand hover:text-white"
            >
              下載 zip
            </a>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
