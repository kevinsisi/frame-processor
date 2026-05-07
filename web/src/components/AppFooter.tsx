import { APP_VERSION } from "@/version";

import "./AppFooter.css";

export function AppFooter() {
  return (
    <footer className="app-footer">
      <div className="app-footer__inner">
        <span className="app-footer__brand">
          Frame <span className="em">·</span> Processor
        </span>
        <span className="app-footer__meta">
          <span className="mono">carsmeet.tw / 8891 · 照片批次後製</span>
          <span className="mono app-footer__version">v{APP_VERSION}</span>
        </span>
      </div>
    </footer>
  );
}
