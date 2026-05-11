import "./AppFooter.css";

export function AppFooter() {
  return (
    <footer className="app-footer">
      <div className="app-footer__inner">
        <span className="app-footer__brand">
          Frame <span className="em">·</span> Processor
        </span>
        <span className="app-footer__meta">
          <span className="mono">照片批次後製</span>
        </span>
      </div>
    </footer>
  );
}
