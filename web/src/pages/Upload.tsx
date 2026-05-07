import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/Card";
import type { Project } from "@/types";

export default function UploadPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((err) => setError(String(err)));
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim() || !files || files.length === 0) {
      setError("請輸入專案名稱並選擇至少一張照片。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const project = await api.createProject(name.trim());
      await api.uploadPhotos(project.id, Array.from(files));
      navigate(`/preview/${project.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card title="新增專案 + 上傳照片">
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">專案名稱</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例：BMW M3 2026-05-07 outdoor"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand focus:ring-2 focus:ring-brand/30 outline-none"
              maxLength={120}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">選擇照片（可多張）</span>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={(e) => setFiles(e.target.files)}
              className="mt-1 block w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-brand file:text-white file:font-medium hover:file:bg-brand-dark"
            />
          </label>
          {files && files.length > 0 ? (
            <div className="text-xs text-slate-500">已選 {files.length} 張</div>
          ) : null}
          {error ? <div className="text-sm text-red-600">{error}</div> : null}
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {busy ? "上傳中…" : "建立並上傳"}
          </button>
        </form>
      </Card>

      <Card title="既有專案">
        {projects.length === 0 ? (
          <div className="text-sm text-slate-500">尚無專案，從左邊建立第一個。</div>
        ) : (
          <ul className="divide-y divide-slate-200">
            {projects.map((project) => (
              <li key={project.id} className="py-2 flex items-center justify-between">
                <div>
                  <div className="font-medium text-slate-800">{project.name}</div>
                  <div className="text-xs text-slate-500">
                    {project.photo_count} 張・{new Date(project.created_at).toLocaleString("zh-TW")}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Link
                    to={`/preview/${project.id}`}
                    className="text-sm px-3 py-1 rounded-md border border-slate-300 hover:bg-slate-50"
                  >
                    預覽
                  </Link>
                  <Link
                    to={`/export/${project.id}`}
                    className="text-sm px-3 py-1 rounded-md border border-slate-300 hover:bg-slate-50"
                  >
                    匯出
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
