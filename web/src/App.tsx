import { Navigate, Route, Routes } from "react-router-dom";

import { AppFooter } from "@/components/AppFooter";
import { AppHeader } from "@/components/AppHeader";
import { ToastProvider } from "@/components/Toast";
import ExportPage from "@/pages/Export";
import PreviewPage from "@/pages/Preview";
import SettingsPage from "@/pages/Settings";
import UploadPage from "@/pages/Upload";

export default function App() {
  return (
    <ToastProvider>
      <AppHeader />
      <Routes>
        <Route path="/" element={<Navigate to="/upload" replace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/preview" element={<PreviewPage />} />
        <Route path="/preview/:projectId" element={<PreviewPage />} />
        <Route path="/export" element={<ExportPage />} />
        <Route path="/export/:projectId" element={<ExportPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
      <AppFooter />
    </ToastProvider>
  );
}
