import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/Card";
import { PhotoGrid } from "@/components/PhotoGrid";
import type { ProjectDetail } from "@/types";

export default function PreviewPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    api.getProject(projectId).then(setProject).catch((err) => setError(String(err)));
  }, [projectId]);

  if (!projectId) {
    return (
      <Card title="預覽">
        <div className="text-sm text-slate-500">
          請從 <Link to="/upload" className="text-brand underline">上傳頁</Link> 選擇一個既有專案。
        </div>
      </Card>
    );
  }

  if (error) {
    return <Card title="預覽">{error}</Card>;
  }

  if (!project) {
    return <Card title="預覽">載入中…</Card>;
  }

  return (
    <Card title={`${project.name}（${project.photo_count} 張）`}>
      <div className="mb-4 flex items-center gap-2">
        <Link
          to={`/export/${project.id}`}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark"
        >
          匯出 zip
        </Link>
        <span className="text-xs text-slate-500">
          v0.1 沒有照片處理；目前只是原圖檢視 + 打包下載。
        </span>
      </div>
      <PhotoGrid photos={project.photos} />
    </Card>
  );
}
