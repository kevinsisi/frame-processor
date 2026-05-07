import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import ExportPage from "@/pages/Export";
import PreviewPage from "@/pages/Preview";
import UploadPage from "@/pages/Upload";

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          "px-4 py-2 rounded-md text-sm font-medium transition-colors",
          isActive ? "bg-brand text-white" : "text-slate-700 hover:bg-slate-200",
        ].join(" ")
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-xl font-semibold text-brand">frame-processor</div>
            <span className="text-xs text-slate-500">v0.1 walking skeleton</span>
          </div>
          <nav className="flex items-center gap-2">
            <NavItem to="/upload" label="上傳" />
            <NavItem to="/preview" label="預覽" />
            <NavItem to="/export" label="匯出" />
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/preview" element={<PreviewPage />} />
          <Route path="/preview/:projectId" element={<PreviewPage />} />
          <Route path="/export" element={<ExportPage />} />
          <Route path="/export/:projectId" element={<ExportPage />} />
        </Routes>
      </main>
    </div>
  );
}
