import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import {
  AdjustmentPanel,
  DEFAULT_ADJUSTMENT_PARAMS,
} from "@/components/AdjustmentPanel";
import { BeforeAfter } from "@/components/BeforeAfter";
import {
  buildPhotoVersionOptions,
  defaultPhotoVersionOption,
  PhotoGrid,
  type PhotoVersionOption,
} from "@/components/PhotoGrid";
import { PipelinePanel } from "@/components/PipelinePanel";
import { Spinner } from "@/components/Spinner";
import { useToast } from "@/components/Toast";
import type {
  AdjustmentParams,
  AdjustmentJob,
  AspectRatio,
  AdjustmentPreset,
  ColorGradePreset,
  CplStrength,
  DenoiseStrength,
  ProcessingJob,
  ProcessingJobCreate,
  ProcessingVersion,
  ProjectDetail,
} from "@/types";
import { needsPipelineRunNote } from "@/utils/pipelinePreview";
import {
  DEFAULT_PIPELINE_DENOISE,
  DEFAULT_PIPELINE_CPL,
  DEFAULT_PIPELINE_PRESET,
  buildPipelinePayload,
  readProjectPipelinePreset,
  writeProjectPipelinePreset,
} from "@/utils/pipelineSettings";

import "./Preview.css";

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("failed to read preview"));
    reader.readAsDataURL(blob);
  });
}

function defaultSelectedPhotoIds(project: ProjectDetail): Set<string> {
  const adjusted = project.photos
    .filter((photo) => photo.adjustment_params || (photo.adjustment_versions ?? []).length > 0)
    .map((photo) => photo.id);
  return new Set(adjusted.length > 0 ? adjusted : project.photos.map((photo) => photo.id));
}

function sourceToVersionValue(source: AdjustmentParams["source"]): string | null {
  if (!source) return null;
  if (source.kind === "original") return "original";
  if (source.kind === "preset" && source.value) return `preset:${source.value}`;
  if (source.kind === "manual" && source.value) return `manual:${source.value}`;
  if (source.kind === "processing" && source.value) return `processing:${source.value}`;
  return null;
}

const PRESET_LABELS: Record<ColorGradePreset, string> = {
  showroom_white: "展示間白",
  outdoor_warm: "戶外暖調",
  night_cold: "夜拍冷調",
};

const DENOISE_LABELS: Record<DenoiseStrength, string> = {
  none: "不降噪",
  light: "輕度降噪",
  medium: "中度降噪",
  heavy: "重度降噪",
};

const CPL_LABELS: Record<CplStrength, string> = {
  none: "不做 CPL Look",
  low: "CPL 輕度",
  medium: "CPL 中度",
  high: "CPL 重度",
};

const ASPECT_LABELS: Record<AspectRatio, string> = {
  original: "原始比例",
  ratio_3_2: "3:2",
  ratio_4_3: "4:3",
  ratio_16_9: "16:9",
  ratio_1_1: "1:1",
  ratio_9_16: "9:16",
};

function processingVersionLabel(version: ProcessingVersion): string {
  return `AI v${version.version_number} · ${PRESET_LABELS[version.preset]} · ${DENOISE_LABELS[version.denoise_strength]} · ${CPL_LABELS[version.cpl_strength]}`;
}

function pipelineMatches(version: ProcessingVersion, payload: ProcessingJobCreate): boolean {
  return (
    version.preset === payload.preset &&
    version.denoise_strength === (payload.denoise_strength ?? "none") &&
    version.lens_distort_correct === (payload.lens_distort_correct ?? false) &&
    version.level_correct === (payload.level_correct ?? false) &&
    version.auto_crop_aspect === (payload.auto_crop_aspect ?? null) &&
    version.cpl_strength === (payload.cpl_strength ?? "none")
  );
}

function photoHasDoneProcessingVersion(
  photo: ProjectDetail["photos"][number],
  versionId: string,
): boolean {
  return Boolean(
    photo.processing_versions?.some(
      (version) => version.processing_job_id === versionId && version.status === "done" && version.path,
    ),
  );
}

function missingPhotoIdsForProcessingVersion(
  project: ProjectDetail,
  version: ProcessingVersion,
): string[] {
  return version.photo_ids.filter((photoId) => {
    const photo = project.photos.find((item) => item.id === photoId);
    return !photo || !photoHasDoneProcessingVersion(photo, version.id);
  });
}

function matchingPipelineOutputMissingPhotoIds(
  project: ProjectDetail,
  payload: ProcessingJobCreate,
): string[] {
  const matchingVersions = project.processing_versions.filter((version) => pipelineMatches(version, payload));
  return project.photos
    .filter(
      (photo) =>
        !matchingVersions.some(
          (version) =>
            (version.status === "done" && photoHasDoneProcessingVersion(photo, version.id)) ||
            ((version.status === "pending" || version.status === "running") && version.photo_ids.includes(photo.id)),
        ),
    )
    .map((photo) => photo.id);
}

function projectInFlightProcessingVersion(project: ProjectDetail): ProcessingVersion | null {
  return project.processing_versions.find((version) => version.status === "pending" || version.status === "running") ?? null;
}

function completedMatchingProcessingVersion(
  project: ProjectDetail,
  payload: ProcessingJobCreate,
  photoIds: string[],
): ProcessingVersion | null {
  return project.processing_versions
    .filter(
      (version) =>
        version.status === "done" &&
        pipelineMatches(version, payload) &&
        photoIds.every((photoId) => {
          const photo = project.photos.find((item) => item.id === photoId);
          return Boolean(photo && version.photo_ids.includes(photoId) && photoHasDoneProcessingVersion(photo, version.id));
        }),
    )
    .sort((a, b) => b.version_number - a.version_number)[0] ?? null;
}

export default function PreviewPage() {
  const { projectId } = useParams();
  const { push: toast } = useToast();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activePhotoId, setActivePhotoId] = useState<string | null>(null);
  const [adjustmentParams, setAdjustmentParams] = useState<AdjustmentParams>(() =>
    structuredClone(DEFAULT_ADJUSTMENT_PARAMS),
  );
  const [preview, setPreview] = useState<{ photoId: string; url: string } | null>(null);
  const [basePreview, setBasePreview] = useState<{ photoId: string; url: string } | null>(null);
  const [photoVersionValues, setPhotoVersionValues] = useState<Record<string, string>>({});
  const [pipelinePreset, setPipelinePreset] = useState<ColorGradePreset>(DEFAULT_PIPELINE_PRESET);
  const [presets, setPresets] = useState<AdjustmentPreset[]>([]);
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [adjustmentJob, setAdjustmentJob] = useState<AdjustmentJob | null>(null);
  const [pipelineBusy, setPipelineBusy] = useState(false);
  const [pipelineDenoise, setPipelineDenoise] = useState<DenoiseStrength>(DEFAULT_PIPELINE_DENOISE);
  const [pipelineLensDistort, setPipelineLensDistort] = useState(true);
  const [pipelineLevelCorrect, setPipelineLevelCorrect] = useState(true);
  const [pipelineAspect, setPipelineAspect] = useState<AspectRatio>("original");
  const [pipelineCplStrength, setPipelineCplStrength] = useState<CplStrength>(DEFAULT_PIPELINE_CPL);
  const [adjustmentBusy, setAdjustmentBusy] = useState(false);
  const [draftDirty, setDraftDirty] = useState(false);
  const pollRef = useRef<number | null>(null);
  const adjustmentPollRef = useRef<number | null>(null);
  const previewRequestRef = useRef(0);
  const basePreviewRequestRef = useRef(0);
  const draftRequestRef = useRef(0);
  const adjustmentPollGenerationRef = useRef(0);
  const adjustmentParamsRef = useRef(adjustmentParams);
  const autoProcessRef = useRef<Set<string>>(new Set());
  const pipelineEditedByUserRef = useRef(false);
  const processingSubmitRef = useRef(false);
  const pollGenerationRef = useRef(0);
  const activeProjectIdRef = useRef(projectId);
  activeProjectIdRef.current = projectId;

  function updateAdjustmentParams(
    params: AdjustmentParams,
    options: { persist?: boolean } = {},
  ) {
    adjustmentParamsRef.current = params;
    setAdjustmentParams(params);
    if (options.persist !== false) setDraftDirty(true);
  }

  async function reload(): Promise<ProjectDetail | null> {
    if (!projectId) return null;
    const requestedProjectId = projectId;
    try {
      const next = await api.getProject(requestedProjectId);
      if (activeProjectIdRef.current !== requestedProjectId) return null;
      setProject(next);
      return next;
    } catch (err) {
      if (activeProjectIdRef.current !== requestedProjectId) return null;
      setError(String(err));
      return null;
    }
  }

  function reloadPresets() {
    if (!projectId) return;
    const requestedProjectId = projectId;
    api
      .listAdjustmentPresets(requestedProjectId)
      .then((nextPresets) => {
        if (activeProjectIdRef.current !== requestedProjectId) return;
        setPresets(nextPresets);
      })
      .catch((err) => {
        if (activeProjectIdRef.current !== requestedProjectId) return;
        toast(`讀取 preset 失敗：${String(err)}`, "error");
      });
  }

  function selectedPhotoVersion(photo: ProjectDetail["photos"][number]): PhotoVersionOption {
    const options = buildPhotoVersionOptions(photo, project?.processing_versions ?? []);
    const draftValue = sourceToVersionValue(photo.adjustment_params?.source);
    const value = photoVersionValues[photo.id] ?? draftValue ?? defaultPhotoVersionOption(options).value;
    return options.find((option) => option.value === value) ?? defaultPhotoVersionOption(options);
  }

  useEffect(() => {
    if (!projectId) {
      pollGenerationRef.current += 1;
      adjustmentPollGenerationRef.current += 1;
      previewRequestRef.current += 1;
      basePreviewRequestRef.current += 1;
      draftRequestRef.current += 1;
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
      if (adjustmentPollRef.current !== null) {
        window.clearInterval(adjustmentPollRef.current);
        adjustmentPollRef.current = null;
      }
      setProject(null);
      setJob(null);
      setAdjustmentJob(null);
      setActivePhotoId(null);
      setPreview(null);
      setBasePreview(null);
      setPipelineBusy(false);
      setAdjustmentBusy(false);
      return;
    }
    setProject(null);
    setError(null);
    setJob(null);
    setAdjustmentJob(null);
    setActivePhotoId(null);
    setPreview(null);
    setBasePreview(null);
    setPipelineBusy(false);
    setAdjustmentBusy(false);
    processingSubmitRef.current = false;
    autoProcessRef.current.clear();
    pipelineEditedByUserRef.current = false;
    pollGenerationRef.current += 1;
    adjustmentPollGenerationRef.current += 1;
    previewRequestRef.current += 1;
    basePreviewRequestRef.current += 1;
    draftRequestRef.current += 1;
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (adjustmentPollRef.current !== null) {
      window.clearInterval(adjustmentPollRef.current);
      adjustmentPollRef.current = null;
    }
    setPipelinePreset(readProjectPipelinePreset(projectId) ?? DEFAULT_PIPELINE_PRESET);
    const requestedProjectId = projectId;
    api
      .getProject(requestedProjectId)
      .then((p) => {
        if (activeProjectIdRef.current !== requestedProjectId) return;
        setProject(p);
        setSelected(defaultSelectedPhotoIds(p));
        setActivePhotoId(
          p.photos.find((ph) => Object.keys(ph.processed_paths ?? {}).length > 0)?.id ??
            p.photos[0]?.id ??
            null,
        );
        reloadPresets();
      })
      .catch((err) => {
        if (activeProjectIdRef.current !== requestedProjectId) return;
        setError(String(err));
      });
  }, [projectId]);

  useEffect(() => {
    adjustmentParamsRef.current = adjustmentParams;
  }, [adjustmentParams]);

  useEffect(() => {
    if (!project || !activePhotoId) return;
    const active = project.photos.find((photo) => photo.id === activePhotoId);
    if (!active) return;
    const source = selectedPhotoVersion(active).source;
    const gradePreset = source.kind === "original" ? pipelinePreset : null;
    updateAdjustmentParams(
      active.adjustment_params
        ? { ...structuredClone(DEFAULT_ADJUSTMENT_PARAMS), ...active.adjustment_params, source, grade_preset: gradePreset }
        : { ...structuredClone(DEFAULT_ADJUSTMENT_PARAMS), source, grade_preset: gradePreset },
      { persist: false },
    );
    setDraftDirty(false);
  }, [activePhotoId, project, pipelinePreset, photoVersionValues]);

  useEffect(() => {
    if (!project || project.id !== projectId) return;
    if (!activePhotoId || !draftDirty) return;
    const requestedProjectId = projectId;
    const requestId = ++draftRequestRef.current;
    const handle = window.setTimeout(async () => {
      try {
        if (activeProjectIdRef.current !== requestedProjectId) return;
        await api.saveAdjustmentDraft(activePhotoId, adjustmentParams);
        if (draftRequestRef.current === requestId && activeProjectIdRef.current === requestedProjectId) setDraftDirty(false);
      } catch (err) {
        console.warn("save adjustment draft failed", err);
      }
    }, 500);
    return () => window.clearTimeout(handle);
  }, [activePhotoId, adjustmentParams, draftDirty, project, projectId]);

  useEffect(() => {
    if (!project || project.id !== projectId) {
      previewRequestRef.current += 1;
      setPreview(null);
      return;
    }
    if (!activePhotoId) {
      setPreview(null);
      return;
    }
    const requestedProjectId = projectId;
    const requestId = ++previewRequestRef.current;
    setPreview(null);
    const handle = window.setTimeout(async () => {
      try {
        if (activeProjectIdRef.current !== requestedProjectId) return;
        const blob = await api.previewAdjustment(activePhotoId, adjustmentParams);
        const url = await blobToDataUrl(blob);
        if (previewRequestRef.current !== requestId || activeProjectIdRef.current !== requestedProjectId) {
          return;
        }
        setPreview({ photoId: activePhotoId, url });
      } catch (err) {
        console.warn("adjustment preview failed", err);
      }
    }, 120);
    return () => window.clearTimeout(handle);
  }, [activePhotoId, adjustmentParams, project, projectId]);

  useEffect(() => {
    if (!project || project.id !== projectId) {
      basePreviewRequestRef.current += 1;
      setBasePreview(null);
      return;
    }
    if (!activePhotoId || adjustmentParams.orientation === 0) {
      basePreviewRequestRef.current += 1;
      setBasePreview(null);
      return;
    }
    const requestedProjectId = projectId;
    const requestId = ++basePreviewRequestRef.current;
    const params = {
      ...structuredClone(DEFAULT_ADJUSTMENT_PARAMS),
      orientation: adjustmentParams.orientation,
      source: adjustmentParams.source,
    };
    const handle = window.setTimeout(async () => {
      try {
        if (activeProjectIdRef.current !== requestedProjectId) return;
        const blob = await api.previewAdjustment(activePhotoId, params);
        const url = await blobToDataUrl(blob);
        if (basePreviewRequestRef.current !== requestId || activeProjectIdRef.current !== requestedProjectId) {
          return;
        }
        setBasePreview({ photoId: activePhotoId, url });
      } catch (err) {
        console.warn("base orientation preview failed", err);
      }
    }, 60);
    return () => window.clearTimeout(handle);
  }, [activePhotoId, adjustmentParams.orientation, adjustmentParams.source, project, projectId]);

  function handlePhotoVersionChange(
    photoId: string,
    value: string,
    option: PhotoVersionOption,
  ) {
    setPhotoVersionValues((prev) => ({ ...prev, [photoId]: value }));
    if (photoId === activePhotoId) {
      updateAdjustmentParams({
        ...adjustmentParamsRef.current,
        source: option.source,
        grade_preset: option.source.kind === "original" ? pipelinePreset : null,
      });
    }
  }

  function handlePipelinePresetChange(preset: ColorGradePreset) {
    pipelineEditedByUserRef.current = true;
    if (projectId) writeProjectPipelinePreset(projectId, preset);
    setPipelinePreset(preset);
    if (adjustmentParamsRef.current.source?.kind === "original") {
      updateAdjustmentParams({ ...adjustmentParamsRef.current, grade_preset: preset });
    }
  }

  function handlePipelineDenoiseChange(denoise: DenoiseStrength) {
    pipelineEditedByUserRef.current = true;
    setPipelineDenoise(denoise);
  }

  function handlePipelineLensDistortChange(enabled: boolean) {
    pipelineEditedByUserRef.current = true;
    setPipelineLensDistort(enabled);
  }

  function handlePipelineLevelCorrectChange(enabled: boolean) {
    pipelineEditedByUserRef.current = true;
    setPipelineLevelCorrect(enabled);
  }

  function handlePipelineAspectChange(aspect: AspectRatio) {
    pipelineEditedByUserRef.current = true;
    setPipelineAspect(aspect);
  }

  function handlePipelineCplStrengthChange(strength: CplStrength) {
    pipelineEditedByUserRef.current = true;
    setPipelineCplStrength(strength);
  }

  function currentPipelinePayload(): ProcessingJobCreate {
    return buildPipelinePayload({
      preset: pipelinePreset,
      denoise: pipelineDenoise,
      lensDistort: pipelineLensDistort,
      levelCorrect: pipelineLevelCorrect,
      aspect: pipelineAspect,
      cplStrength: pipelineCplStrength,
    });
  }

  function beginProcessingPoll(
    jobId: string,
    options: {
      automatic?: boolean;
      selectOnDone?: boolean;
      submittedPhotoIds?: string[];
      showDoneToast?: boolean;
    } = {},
  ) {
    if (pollRef.current !== null) window.clearInterval(pollRef.current);
    const pollGeneration = pollGenerationRef.current + 1;
    const pollProjectId = activeProjectIdRef.current;
    pollGenerationRef.current = pollGeneration;
    pollRef.current = window.setInterval(async () => {
      try {
        const next = await api.getProcessingJob(jobId);
        if (pollGenerationRef.current !== pollGeneration || activeProjectIdRef.current !== pollProjectId) return;
        setJob(next);
        if (next.status === "done" || next.status === "failed") {
          if (pollRef.current !== null) {
            window.clearInterval(pollRef.current);
            pollRef.current = null;
          }
          processingSubmitRef.current = false;
          setPipelineBusy(false);
          if (next.status === "done") {
            if (options.showDoneToast) {
              toast(options.automatic ? "AI 版本已產生" : "處理完成", "success");
            }
            if (options.submittedPhotoIds) {
              setPhotoVersionValues((prev) => ({
                ...prev,
                ...Object.fromEntries(options.submittedPhotoIds!.map((photoId) => [photoId, `processing:${jobId}`])),
              }));
            }
            const fresh = await reload();
            if (pollGenerationRef.current !== pollGeneration || activeProjectIdRef.current !== pollProjectId) return;
            if ((options.selectOnDone ?? true) && fresh) selectProcessingVersion(jobId, fresh);
          } else if (options.showDoneToast) {
            toast(`處理失敗：${next.error ?? "unknown error"}`, "error");
          } else {
            await reload();
          }
        }
      } catch (err) {
        console.warn("poll processing job failed", err);
      }
    }, 2000);
  }

  useEffect(() => {
    return () => {
      activeProjectIdRef.current = undefined;
      pollGenerationRef.current += 1;
      adjustmentPollGenerationRef.current += 1;
      previewRequestRef.current += 1;
      basePreviewRequestRef.current += 1;
      draftRequestRef.current += 1;
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
      if (adjustmentPollRef.current !== null) {
        window.clearInterval(adjustmentPollRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!project || !projectId || pollRef.current !== null) return;
    const inFlight =
      job?.status === "pending" || job?.status === "running"
        ? job
        : projectInFlightProcessingVersion(project);
    if (!inFlight) return;
    setJob(inFlight);
    beginProcessingPoll(inFlight.id);
  }, [project, projectId, job?.status]);

  useEffect(() => {
    const pipelineRunning =
      pipelineBusy ||
      job?.status === "pending" ||
      job?.status === "running" ||
      (project ? projectInFlightProcessingVersion(project) !== null : false);
    if (!project || !projectId || pipelineRunning) return;
    if (pipelineEditedByUserRef.current) return;
    const payload = currentPipelinePayload();
    const missingPhotoIds = matchingPipelineOutputMissingPhotoIds(project, payload);
    if (missingPhotoIds.length === 0) return;
    const key = `${project.id}:${JSON.stringify(payload)}:${missingPhotoIds.join(",")}`;
    if (autoProcessRef.current.has(key)) return;
    autoProcessRef.current.add(key);
    void startProcessing(
      payload,
      missingPhotoIds,
      { automatic: true },
    );
  }, [project, projectId, pipelineBusy, pipelinePreset, pipelineDenoise, pipelineLensDistort, pipelineLevelCorrect, pipelineAspect, pipelineCplStrength, job?.status]);

  function toggle(photoId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(photoId)) {
        next.delete(photoId);
      } else {
        next.add(photoId);
      }
      return next;
    });
  }

  function selectAll() {
    if (!project) return;
    setSelected(new Set(project.photos.map((p) => p.id)));
  }

  function selectAdjusted() {
    if (!project) return;
    setSelected(defaultSelectedPhotoIds(project));
  }

  function selectNone() {
    setSelected(new Set());
  }

  function navigateComparison(direction: -1 | 1) {
    if (!project || project.photos.length <= 1) return;
    const currentIndex = project.photos.findIndex(
      (photo) => photo.id === (activePhotoId ?? project.photos[0]?.id),
    );
    const safeIndex = currentIndex >= 0 ? currentIndex : 0;
    const nextIndex = (safeIndex + direction + project.photos.length) % project.photos.length;
    setActivePhotoId(project.photos[nextIndex].id);
  }

  async function handleSubmit(payload: ProcessingJobCreate) {
    if (processingSubmitRef.current || pipelineBusy || job?.status === "pending" || job?.status === "running") return;
    if (project) {
      const currentInFlight = projectInFlightProcessingVersion(project);
      if (currentInFlight) {
        setJob(currentInFlight);
        beginProcessingPoll(currentInFlight.id);
        toast(`已有 AI v${currentInFlight.version_number} 產生中，已切換為追蹤進度`, "info");
        return;
      }
    }
    processingSubmitRef.current = true;
    const submittedPhotoIds = Array.from(selected);
    const completedAtClick = project ? completedMatchingProcessingVersion(project, payload, submittedPhotoIds) : null;
    const fresh = await reload();
    if (activeProjectIdRef.current !== projectId) {
      processingSubmitRef.current = false;
      return;
    }
    const inFlight = fresh ? projectInFlightProcessingVersion(fresh) : null;
    if (inFlight) {
      setJob(inFlight);
      beginProcessingPoll(inFlight.id);
      toast(`已有 AI v${inFlight.version_number} 產生中，已切換為追蹤進度`, "info");
      return;
    }
    const completedAfterReload = fresh ? completedMatchingProcessingVersion(fresh, payload, submittedPhotoIds) : null;
    if (completedAfterReload && completedAfterReload.id !== completedAtClick?.id) {
      setJob(completedAfterReload);
      selectProcessingVersion(completedAfterReload.id, fresh ?? undefined);
      processingSubmitRef.current = false;
      toast(`AI v${completedAfterReload.version_number} 已完成，已切換到完成版本`, "success");
      return;
    }
    await startProcessing(
      payload,
      submittedPhotoIds,
      { automatic: false, lockHeld: true, completedBaselineId: completedAtClick?.id ?? null },
      fresh ?? project,
    );
  }

  function selectProcessingVersion(jobId: string, sourceProject?: ProjectDetail) {
    const targetProject = sourceProject ?? project;
    if (!targetProject) return;
    const nextValues = Object.fromEntries(
      targetProject.photos
        .filter((photo) => photoHasDoneProcessingVersion(photo, jobId))
        .map((photo) => [photo.id, `processing:${jobId}`]),
    );
    setPhotoVersionValues((prev) => ({
      ...prev,
      ...nextValues,
    }));
    if (activePhotoId && nextValues[activePhotoId]) {
      updateAdjustmentParams({
        ...adjustmentParamsRef.current,
        source: { kind: "processing", value: jobId },
        grade_preset: null,
      });
    }
  }

  async function archiveProcessingVersion(jobId: string) {
    if (!project || !window.confirm("確定要隱藏這個 AI 版本？檔案會保留，但預設列表不再顯示。")) return;
    try {
      await api.archiveProcessingVersion(jobId);
      const next = project.processing_versions.find((version) => version.id !== jobId);
      setPhotoVersionValues((prev) => {
        const entries = Object.entries(prev).filter(([, value]) => value !== `processing:${jobId}`);
        return Object.fromEntries(entries);
      });
      const fresh = await reload();
      if (next && fresh) selectProcessingVersion(next.id, fresh);
      toast("AI 版本已隱藏", "success");
    } catch (err) {
      toast(`隱藏 AI 版本失敗：${String(err)}`, "error");
    }
  }

  function retryProcessingVersion(version: ProcessingVersion, scope: "full" | "missing_only") {
    if (!project) return;
    const photoIds = scope === "missing_only" ? missingPhotoIdsForProcessingVersion(project, version) : version.photo_ids;
    if (photoIds.length === 0) {
      toast("這個 AI 版本沒有缺漏照片需要重試", "info");
      return;
    }
    void startProcessing(
      {
        preset: version.preset,
        denoise_strength: version.denoise_strength,
        lens_distort_correct: version.lens_distort_correct,
        level_correct: version.level_correct,
        auto_crop_aspect: version.auto_crop_aspect,
        cpl_strength: version.cpl_strength,
        force: true,
        retry_scope: scope,
        retry_of_job_id: version.id,
      },
      photoIds,
      { automatic: false, completedBaselineId: version.id },
    );
  }

  async function startProcessing(
    payload: ProcessingJobCreate,
    photoIds: string[],
    options: { automatic: boolean; lockHeld?: boolean; completedBaselineId?: string | null },
    sourceProject: ProjectDetail | null = project,
  ) {
    if (!options.lockHeld) {
      if (processingSubmitRef.current) return;
      processingSubmitRef.current = true;
    }
    if (!projectId || !sourceProject) {
      processingSubmitRef.current = false;
      return;
    }
    if (job?.status === "pending" || job?.status === "running" || projectInFlightProcessingVersion(sourceProject) !== null) {
      processingSubmitRef.current = false;
      return;
    }
    if (photoIds.length === 0) {
      processingSubmitRef.current = false;
      return;
    }
    const submittedPhotoIds = photoIds;
    const submittedProjectId = projectId;
    if (activeProjectIdRef.current !== submittedProjectId) {
      processingSubmitRef.current = false;
      return;
    }
    setPipelineBusy(true);
    try {
      const created = await api.createProcessingJob(submittedProjectId, {
        ...payload,
        photo_ids: submittedPhotoIds,
      });
      if (activeProjectIdRef.current !== submittedProjectId) {
        processingSubmitRef.current = false;
        return;
      }
      if (options.automatic && pipelineEditedByUserRef.current) {
        processingSubmitRef.current = false;
        setPipelineBusy(false);
        return;
      }
      setJob(created);
      toast(
        options.automatic
          ? `已自動開始產生 AI 版本，共 ${created.total} 張`
          : `已開始處理，共 ${created.total} 張`,
        "info",
      );
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
      beginProcessingPoll(created.id, {
        automatic: options.automatic,
        selectOnDone: true,
        submittedPhotoIds,
        showDoneToast: true,
      });
    } catch (err) {
      if (activeProjectIdRef.current !== submittedProjectId) {
        processingSubmitRef.current = false;
        return;
      }
      setPipelineBusy(false);
      const fresh = await reload();
      if (activeProjectIdRef.current !== submittedProjectId) {
        processingSubmitRef.current = false;
        return;
      }
      const inFlight = fresh ? projectInFlightProcessingVersion(fresh) : null;
      if (inFlight) {
        setJob(inFlight);
        beginProcessingPoll(inFlight.id);
        toast(`已有 AI v${inFlight.version_number} 產生中，已切換為追蹤進度`, "info");
      } else {
        const completed = fresh ? completedMatchingProcessingVersion(fresh, payload, submittedPhotoIds) : null;
        if (completed && completed.id !== options.completedBaselineId) {
          setJob(completed);
          selectProcessingVersion(completed.id, fresh ?? undefined);
          toast(`AI v${completed.version_number} 已完成，已切換到完成版本`, "success");
          processingSubmitRef.current = false;
        } else {
          toast(`建立處理 job 失敗：${String(err)}`, "error");
          processingSubmitRef.current = false;
        }
      }
    }
  }

  async function applyAdjustment(photoIds: string[]) {
    if (photoIds.length === 0) return;
    const submittedProjectId = projectId;
    if (!submittedProjectId) return;
    setAdjustmentBusy(true);
    try {
      if (photoIds.length === 1) {
        await api.applyAdjustment(photoIds[0], adjustmentParams);
        if (activeProjectIdRef.current !== submittedProjectId) return;
        toast("已套用微調", "success");
        reload();
        setAdjustmentBusy(false);
        return;
      }
      if (!submittedProjectId) {
        setAdjustmentBusy(false);
        return;
      }
      const sources = Object.fromEntries(
        photoIds
          .map((photoId) => {
            const photo = project?.photos.find((item) => item.id === photoId);
            return photo ? [photoId, selectedPhotoVersion(photo).source] : null;
          })
          .filter((item): item is [string, PhotoVersionOption["source"]] => item !== null),
      );
      const created = await api.createAdjustmentJob(
        submittedProjectId,
        adjustmentParams,
        photoIds,
        sources,
      );
      if (activeProjectIdRef.current !== submittedProjectId) return;
      setAdjustmentJob(created);
      toast(`已開始套用微調，共 ${created.total} 張`, "info");
      if (adjustmentPollRef.current !== null) {
        window.clearInterval(adjustmentPollRef.current);
      }
      const adjustmentPollGeneration = adjustmentPollGenerationRef.current + 1;
      adjustmentPollGenerationRef.current = adjustmentPollGeneration;
      adjustmentPollRef.current = window.setInterval(async () => {
        try {
          const next = await api.getAdjustmentJob(created.id);
          if (adjustmentPollGenerationRef.current !== adjustmentPollGeneration || activeProjectIdRef.current !== submittedProjectId) return;
          setAdjustmentJob(next);
          if (next.status === "done" || next.status === "failed") {
            if (adjustmentPollRef.current !== null) {
              window.clearInterval(adjustmentPollRef.current);
              adjustmentPollRef.current = null;
            }
            setAdjustmentBusy(false);
            if (next.status === "done") {
              toast("批次微調完成", "success");
              reload();
            } else {
              toast(`批次微調失敗：${next.error ?? "unknown error"}`, "error");
            }
          }
        } catch (err) {
          console.warn("poll adjustment job failed", err);
        }
      }, 1500);
    } catch (err) {
      if (activeProjectIdRef.current !== submittedProjectId) return;
      toast(`套用微調失敗：${String(err)}`, "error");
      setAdjustmentBusy(false);
    }
  }

  function rotateActivePhoto(direction: "left" | "right") {
    if (!activePhotoId) return;
    const current = adjustmentParamsRef.current;
    const delta = direction === "right" ? 90 : 270;
    const next = {
      ...current,
      orientation: (current.orientation + delta) % 360,
    };
    updateAdjustmentParams(next);
  }

  async function savePreset(name: string) {
    const requestedProjectId = projectId;
    if (!requestedProjectId) return;
    try {
      // Manual presets store slider edits only; pipeline color style remains a separate choice.
      const { source: _source, grade_preset: _gradePreset, ...presetParams } = adjustmentParams;
      await api.createAdjustmentPreset(name, presetParams, requestedProjectId);
      if (activeProjectIdRef.current !== requestedProjectId) return;
      toast("已儲存 preset", "success");
      reloadPresets();
    } catch (err) {
      if (activeProjectIdRef.current !== requestedProjectId) return;
      toast(`儲存 preset 失敗：${String(err)}`, "error");
    }
  }

  async function deletePreset(preset: AdjustmentPreset) {
    const requestedProjectId = projectId;
    if (!requestedProjectId) return;
    try {
      await api.deleteAdjustmentPreset(preset.id);
      if (activeProjectIdRef.current !== requestedProjectId) return;
      toast(`已刪除 preset：${preset.name}`, "success");
      reloadPresets();
    } catch (err) {
      if (activeProjectIdRef.current !== requestedProjectId) return;
      toast(`刪除 preset 失敗：${String(err)}`, "error");
    }
  }

  if (!projectId) {
    return (
      <main className="page page--narrow preview-empty">
        <section className="hero">
          <div className="hero__kicker">預覽</div>
          <h1 className="hero__title">
            還沒選<em>專案</em>。
          </h1>
          <p className="hero__lede">從上傳頁建立或選一個既有專案。</p>
        </section>
        <Link to="/upload" className="cta cta--primary">
          ← 回到上傳頁
        </Link>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page preview">
        <section className="hero">
          <div className="hero__kicker">預覽 · 錯誤</div>
          <h1 className="hero__title">
            讀不到<em>專案</em>。
          </h1>
        </section>
        <div className="alert" role="alert">
          {error}
        </div>
        <Link to="/upload" className="cta cta--quiet preview__back">
          ← 回到上傳頁
        </Link>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="page preview">
        <section className="hero">
          <div className="hero__kicker">預覽</div>
          <h1 className="hero__title">載入中…</h1>
        </section>
        <Spinner label="正在讀取專案" />
      </main>
    );
  }

  const activePhoto = project.photos.find((p) => p.id === activePhotoId) ?? null;
  const samplePhoto =
    activePhoto ??
    project.photos.find((p) => Object.keys(p.processed_paths ?? {}).length > 0) ??
    null;
  const samplePhotoIndex = samplePhoto
    ? project.photos.findIndex((photo) => photo.id === samplePhoto.id)
    : -1;
  const processingVersions = project.processing_versions.map((version) => (job?.id === version.id ? job : version));
  const inFlightProcessingVersion = projectInFlightProcessingVersion(project);
  const displayedJob = job && inFlightProcessingVersion?.id === job.id ? job : inFlightProcessingVersion ?? job;
  const sampleVersion = samplePhoto ? selectedPhotoVersion(samplePhoto) : null;
  const renderPipelinePayload = currentPipelinePayload();
  const sampleHasMatchingPipelineOutput = Boolean(
    samplePhoto &&
      processingVersions.some(
        (version) =>
          version.status === "done" &&
          pipelineMatches(version, renderPipelinePayload) &&
          photoHasDoneProcessingVersion(samplePhoto, version.id),
      ),
  );
  const resolvedPhotoVersionValues = Object.fromEntries(
    project.photos.map((photo) => [photo.id, selectedPhotoVersion(photo).value]),
  );
  const activePreviewUrl =
    preview && preview.photoId === samplePhoto?.id ? preview.url : null;
  const activeBasePreviewUrl =
    basePreview && basePreview.photoId === samplePhoto?.id ? basePreview.url : null;
  const baseDisplayUrl = sampleVersion?.url ?? "";
  const originalDisplayUrl = samplePhoto ? api.photoFileUrl(samplePhoto.id) : "";
  const needsPipelineRun = needsPipelineRunNote({
    sourceKind: sampleVersion?.source.kind,
    hasMatchingPipelineOutput: sampleHasMatchingPipelineOutput,
    hasActivePreview: Boolean(activePreviewUrl),
  });
  const progressPct =
    displayedJob && displayedJob.total > 0 ? Math.round((displayedJob.progress / displayedJob.total) * 100) : 0;
  const pipelineRunning = pipelineBusy || displayedJob?.status === "pending" || displayedJob?.status === "running";
  const pipelineActionLabel = pipelineRunning ? "產生中…" : "開始產生";
  const pipelineActionDisabled = pipelineRunning || selected.size === 0;
  const pipelineStatusLabel = pipelineRunning
    ? `正在產生 ${displayedJob?.progress ?? 0} / ${displayedJob?.total ?? selected.size} 張`
    : displayedJob?.status === "done"
      ? "上一批已完成"
      : displayedJob?.status === "failed"
        ? "上一批失敗"
        : "準備產生";
  const adjustmentProgressPct =
    adjustmentJob && adjustmentJob.total > 0
      ? Math.round((adjustmentJob.progress / adjustmentJob.total) * 100)
      : 0;
  const selectedProcessingVersionIds = Array.from(
    new Set(
      Object.values(resolvedPhotoVersionValues)
        .filter((value) => value.startsWith("processing:"))
        .map((value) => value.slice("processing:".length)),
    ),
  );

  return (
    <main className="page preview">
      <section className="hero preview__hero">
        <div className="hero__kicker">
          預覽 · 專案 #{String(project.id).slice(0, 8)}
        </div>
        <h1 className="hero__title">{project.name}</h1>
        <p className="hero__lede">{project.photo_count} 張照片</p>
      </section>

      <section className="preview-action" aria-label="目前處理設定與產生動作">
        <div className="preview-action__main">
          <span className="preview-action__eyebrow mono">目前處理設定</span>
          <strong>{PRESET_LABELS[pipelinePreset]}</strong>
          <span>
            {DENOISE_LABELS[pipelineDenoise]} · {CPL_LABELS[pipelineCplStrength]} · {pipelineLensDistort ? "廣角矯正" : "不做廣角矯正"} · {pipelineLevelCorrect ? "水平校正" : "不做水平校正"} · {ASPECT_LABELS[pipelineAspect]}
          </span>
        </div>
        <div className="preview-action__side">
          <span className="preview-action__status mono">{pipelineStatusLabel}</span>
          <button
            type="button"
            className="cta cta--primary"
            onClick={() => void handleSubmit(currentPipelinePayload())}
            disabled={pipelineActionDisabled}
          >
            {pipelineActionLabel}
          </button>
        </div>
      </section>

      {displayedJob && (
        <section className="job-status">
          <header className="job-status__head">
            <span className="mono">job #{displayedJob.id.slice(0, 8)}</span>
            <span className={`job-status__pill job-status__pill--${displayedJob.status}`}>
              {displayedJob.status}
            </span>
          </header>
          <div className="job-status__bar" aria-hidden>
            <div
              className="job-status__bar-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <p className="job-status__meta mono">
            {displayedJob.progress} / {displayedJob.total} 完成
            {displayedJob.error ? ` · ${displayedJob.error}` : ""}
          </p>
          <ol className="job-status__queue">
            {displayedJob.photo_ids.map((pid, idx) => {
              const photo = project.photos.find((p) => p.id === pid);
              const name = photo?.original_filename ?? pid.slice(0, 8);
              let state: "done" | "running" | "queued" = "queued";
              if (displayedJob.status === "done") state = "done";
              else if (idx < displayedJob.progress) state = "done";
              else if (idx === displayedJob.progress && displayedJob.status === "running")
                state = "running";
              const icon = state === "done" ? "✓" : state === "running" ? "●" : "○";
              return (
                <li key={pid} className={`job-status__queue-item job-status__queue-item--${state}`}>
                  <span className="job-status__queue-icon" aria-hidden>{icon}</span>
                  <span className="job-status__queue-idx mono">
                    {String(idx + 1).padStart(String(displayedJob.total).length, "0")}/{displayedJob.total}
                  </span>
                  <span className="job-status__queue-name" title={name}>{name}</span>
                  <span className="job-status__queue-state mono">{state === "running" ? "處理中" : state === "done" ? "完成" : "等待中"}</span>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {processingVersions.length > 0 && (
        <section className="section ai-versions" aria-label="AI 批次版本">
          <header className="section__head">
            <h2 className="section__title">AI 批次版本</h2>
            <span className="section__meta mono">
              {processingVersions.length} 個版本
              {selectedProcessingVersionIds.length === 1 ? ` · 目前 AI v${processingVersions.find((version) => version.id === selectedProcessingVersionIds[0])?.version_number ?? ""}` : ""}
            </span>
          </header>
          <div className="ai-version-list">
            {processingVersions.map((version) => {
              const missingPhotoIds = missingPhotoIdsForProcessingVersion(project, version);
              const missingNames = missingPhotoIds.map(
                (photoId) => project.photos.find((photo) => photo.id === photoId)?.original_filename ?? photoId.slice(0, 8),
              );
              const isRunning = version.status === "pending" || version.status === "running";
              const canExport = version.status === "done" || missingPhotoIds.length < version.photo_ids.length;
              return (
                <article key={version.id} className="ai-version-card">
                  <div className="ai-version-card__main">
                    <strong>{processingVersionLabel(version)}</strong>
                    <span className={`job-status__pill job-status__pill--${version.status}`}>{version.status}</span>
                    <span className="ai-version-card__meta mono">
                      {version.progress} / {version.total} 完成
                      {missingPhotoIds.length > 0 ? ` · 缺 ${missingPhotoIds.length} 張` : ""}
                      {version.retry_scope !== "none" ? ` · retry ${version.retry_scope}` : ""}
                    </span>
                    <span className="ai-version-card__settings">
                      {CPL_LABELS[version.cpl_strength]} · {version.lens_distort_correct ? "廣角矯正" : "不做廣角矯正"} · {version.level_correct ? "水平校正" : "不做水平校正"} · {ASPECT_LABELS[version.auto_crop_aspect ?? "original"]}
                    </span>
                    {missingNames.length > 0 ? (
                      <span className="ai-version-card__error">缺漏照片：{missingNames.slice(0, 6).join("、")}{missingNames.length > 6 ? "…" : ""}</span>
                    ) : null}
                    {version.error ? <span className="ai-version-card__error">{version.error}</span> : null}
                  </div>
                  <div className="ai-version-card__actions">
                    <button
                      type="button"
                      className="bulk-bar__btn"
                      onClick={() => selectProcessingVersion(version.id)}
                      disabled={missingPhotoIds.length === version.photo_ids.length}
                    >
                      查看版本
                    </button>
                    <button
                      type="button"
                      className="bulk-bar__btn"
                      onClick={() => retryProcessingVersion(version, "full")}
                      disabled={pipelineRunning || isRunning}
                    >
                      重試全部
                    </button>
                    <button
                      type="button"
                      className="bulk-bar__btn"
                      onClick={() => retryProcessingVersion(version, "missing_only")}
                      disabled={pipelineRunning || isRunning || missingPhotoIds.length === 0}
                    >
                      只補缺漏
                    </button>
                    {canExport ? (
                      <Link to={`/export/${project.id}?processing_job_id=${version.id}`} className="bulk-bar__btn">
                        匯出此版
                      </Link>
                    ) : null}
                    <button
                      type="button"
                      className="bulk-bar__btn bulk-bar__btn--danger"
                      onClick={() => void archiveProcessingVersion(version.id)}
                      disabled={isRunning}
                    >
                      隱藏
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      {samplePhoto && (
        <section className="section">
          <header className="section__head">
            <h2 className="section__title">前後對比</h2>
            <span className="section__meta mono">
              {activePreviewUrl ? "目前微調" : sampleVersion?.label ?? "原圖"}
            </span>
          </header>
          <div className="preview-compare">
            <BeforeAfter
              key={`${samplePhoto.id}:${adjustmentParams.orientation}:${sampleVersion?.value ?? "original"}`}
              beforeUrl={originalDisplayUrl}
              afterUrl={
                activePreviewUrl ??
                (sampleVersion?.url ?? api.photoFileUrl(samplePhoto.id))
              }
              alt={samplePhoto.original_filename}
            />
            {project.photos.length > 1 && (
              <>
                <button
                  type="button"
                  className="preview-compare__nav preview-compare__nav--prev"
                  onClick={() => navigateComparison(-1)}
                  aria-label="查看上一張照片"
                >
                  <span aria-hidden>‹</span>
                  <strong>上一張</strong>
                </button>
                <button
                  type="button"
                  className="preview-compare__nav preview-compare__nav--next"
                  onClick={() => navigateComparison(1)}
                  aria-label="查看下一張照片"
                >
                  <strong>下一張</strong>
                  <span aria-hidden>›</span>
                </button>
                <div className="preview-compare__counter mono">
                  {samplePhotoIndex + 1} / {project.photos.length} · {samplePhoto.original_filename}
                </div>
              </>
            )}
          </div>
          {needsPipelineRun && (
            <div className="preview__pipeline-note">
              <div>
                <strong>原圖會保留未降噪，AI 版本會在背景產生。</strong>
                <span>這張照片還沒有批次處理版本；系統會依目前處理設定自動產生 AI 版本，完成後右側會切到處理後。</span>
              </div>
              <a className="cta cta--primary" href="#pipeline-settings">前往開始產生</a>
            </div>
          )}
        </section>
      )}

      {adjustmentJob && (
        <section className="job-status">
          <header className="job-status__head">
            <span className="mono">adjust #{adjustmentJob.id.slice(0, 8)}</span>
            <span className={`job-status__pill job-status__pill--${adjustmentJob.status}`}>
              {adjustmentJob.status}
            </span>
          </header>
          <div className="job-status__bar" aria-hidden>
            <div
              className="job-status__bar-fill"
              style={{ width: `${adjustmentProgressPct}%` }}
            />
          </div>
          <p className="job-status__meta mono">
            {adjustmentJob.progress} / {adjustmentJob.total} 微調完成
            {adjustmentJob.error ? ` · ${adjustmentJob.error}` : ""}
          </p>
        </section>
      )}

      {activePhotoId && (
        <AdjustmentPanel
          params={adjustmentParams}
          presets={presets}
          geometryBaseUrl={activeBasePreviewUrl ?? baseDisplayUrl}
          busy={adjustmentBusy}
          onChange={updateAdjustmentParams}
          onApplyCurrent={() => void applyAdjustment([activePhotoId])}
          onApplySelected={() => void applyAdjustment(Array.from(selected))}
          onReset={() =>
            updateAdjustmentParams({
              ...structuredClone(DEFAULT_ADJUSTMENT_PARAMS),
              source: adjustmentParams.source,
              grade_preset: adjustmentParams.grade_preset ?? null,
            })
          }
          onSavePreset={(name) => void savePreset(name)}
          onLoadPreset={(preset) =>
            updateAdjustmentParams({
              ...preset.params,
              source: adjustmentParamsRef.current.source,
              grade_preset: adjustmentParamsRef.current.grade_preset ?? null,
            })
          }
          onDeletePreset={(preset) => void deletePreset(preset)}
          onRotateLeft={() => rotateActivePhoto("left")}
          onRotateRight={() => rotateActivePhoto("right")}
        />
      )}

      <div id="pipeline-settings">
        <PipelinePanel
          selectedCount={selected.size}
          totalCount={project.photos.length}
          busy={pipelineRunning}
          preset={pipelinePreset}
          denoise={pipelineDenoise}
          lensDistort={pipelineLensDistort}
          levelCorrect={pipelineLevelCorrect}
          aspect={pipelineAspect}
          cplStrength={pipelineCplStrength}
          onPresetChange={handlePipelinePresetChange}
          onDenoiseChange={handlePipelineDenoiseChange}
          onLensDistortChange={handlePipelineLensDistortChange}
          onLevelCorrectChange={handlePipelineLevelCorrectChange}
          onAspectChange={handlePipelineAspectChange}
          onCplStrengthChange={handlePipelineCplStrengthChange}
          onSubmit={handleSubmit}
        />
      </div>

      <section className="section">
        <header className="section__head">
          <h2 className="section__title">照片清單</h2>
          <span className="section__meta">
            {selected.size} / {project.photos.length} 已選
          </span>
        </header>

        <div className="bulk-bar">
          <div className="bulk-bar__group">
            <button
              type="button"
              className="bulk-bar__btn"
              onClick={selectAll}
              disabled={selected.size === project.photos.length}
            >
              全選
            </button>
            <button
              type="button"
              className="bulk-bar__btn"
              onClick={selectAdjusted}
            >
              只選已調整
            </button>
            <button
              type="button"
              className="bulk-bar__btn"
              onClick={selectNone}
              disabled={selected.size === 0}
            >
              取消全選
            </button>
          </div>
          <div className="bulk-bar__group">
            <Link to={`/export/${project.id}`} className="cta cta--primary">
              匯出 zip →
            </Link>
          </div>
        </div>

        <PhotoGrid
          photos={project.photos}
          selectable
          selectedIds={selected}
          activeId={samplePhoto?.id ?? activePhotoId}
          versionValues={resolvedPhotoVersionValues}
          processingVersions={processingVersions}
          onToggleSelect={toggle}
          onOpenPreview={setActivePhotoId}
          onVersionChange={handlePhotoVersionChange}
        />
      </section>
    </main>
  );
}
