import type { ProcessingJob } from "@/types";

import "./ProcessingProgress.css";

export interface ProcessingProgressProps {
  job: ProcessingJob;
}

const STATUS_LABEL: Record<ProcessingJob["status"], string> = {
  pending: "排隊中",
  running: "處理中",
  done: "已完成",
  failed: "失敗",
};

export function ProcessingProgress({ job }: ProcessingProgressProps) {
  const total = Math.max(job.progress_total, 1);
  const pct = Math.min(100, Math.round((job.progress_done / total) * 100));
  const isRunning = job.status === "running" || job.status === "pending";
  return (
    <div className={`processing-progress processing-progress--${job.status}`}>
      <div className="processing-progress__head">
        <span className="processing-progress__label mono">
          {STATUS_LABEL[job.status]}
          {isRunning ? "…" : ""}
        </span>
        <span className="processing-progress__count mono">
          {job.progress_done} / {job.progress_total}
        </span>
      </div>
      <div className="processing-progress__bar" aria-hidden>
        <div
          className="processing-progress__fill"
          style={{ width: `${pct}%` }}
        />
      </div>
      {job.error ? (
        <pre className="processing-progress__error mono">{job.error}</pre>
      ) : null}
    </div>
  );
}
