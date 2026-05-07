import "./Spinner.css";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <span className="spinner__ring" aria-hidden />
      {label ? <span className="spinner__label mono">{label}</span> : null}
    </div>
  );
}
