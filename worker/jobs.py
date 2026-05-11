"""RQ job 函數。

- ``zip_export_job``：打包專案輸出為 zip。優先採用每張照片的最新處理結果，
  若無則 fallback 到原圖。
- ``process_photos_job``：對 ProcessingJob 列出的 photo 跑 pipeline，
  把結果路徑寫回 ``Photo.processed_paths``，並更新 progress / status。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from api.config import settings
from api.database import SessionLocal
from models.adjustment_job import AdjustmentJob
from models.enums import ExportStatus, ProcessingJobStatus
from models.export import Export
from models.photo import Photo
from models.photo_processing_version import PhotoProcessingVersion
from models.processing_job import ProcessingJob
from services import adjustment_renderer, photo_processor, processing_versions, zip_export


def zip_export_job(export_id: str) -> str:
    export_uuid = UUID(export_id)

    with SessionLocal() as db:
        export = db.get(Export, export_uuid)
        if export is None:
            raise ValueError(f"export {export_id} not found")

        export.status = ExportStatus.RUNNING
        db.commit()

        try:
            payload = _version_export_payload(db, export) if export.processing_job_id else _legacy_export_payload(db, export)

            zip_abs = zip_export.build_zip(export_id=export_uuid, photos=payload)
            export.zip_path = zip_export.relative_to_storage(zip_abs)
            export.status = ExportStatus.DONE
            export.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            return export.zip_path
        except Exception as exc:
            export.status = ExportStatus.FAILED
            export.error = str(exc)
            export.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            raise


def _pick_export_path(stored_path: str, processed_paths: dict[str, str] | None) -> str:
    """有手動調整優先用 adjusted，否則用任一處理結果，最後 fallback 原圖。"""
    if processed_paths:
        adjusted = processed_paths.get("adjusted")
        if adjusted:
            return adjusted
        for value in processed_paths.values():
            if value:
                return value
    return stored_path


def _legacy_export_payload(db, export: Export) -> list[tuple[str, str]]:
    photos = (
        db.execute(
            select(
                Photo.original_filename,
                Photo.stored_path,
                Photo.processed_paths,
            ).where(Photo.project_id == export.project_id)
        )
        .tuples()
        .all()
    )
    payload: list[tuple[str, str]] = []
    for original_name, stored_path, processed_paths in photos:
        relative = _pick_export_path(stored_path, processed_paths)
        payload.append((original_name, relative))
    return payload


def _version_export_payload(db, export: Export) -> list[tuple[str, str]]:
    job = db.get(ProcessingJob, export.processing_job_id)
    if job is None or job.archived_at is not None:
        raise ValueError("selected AI version is unavailable")
    photos = (
        db.execute(
            select(Photo.id, Photo.original_filename)
            .where(Photo.project_id == export.project_id, Photo.id.in_(job.photo_ids or []))
            .order_by(Photo.uploaded_at)
        )
        .tuples()
        .all()
    )
    rows = (
        db.execute(
            select(
                PhotoProcessingVersion.photo_id,
                PhotoProcessingVersion.path,
                PhotoProcessingVersion.status,
            )
            .where(
                PhotoProcessingVersion.processing_job_id == export.processing_job_id,
            )
        )
        .tuples()
        .all()
    )
    rows_by_photo = {photo_id: (path, row_status) for photo_id, path, row_status in rows}
    payload: list[tuple[str, str]] = []
    missing: list[str] = []
    for photo_id, original_name in photos:
        path, row_status = rows_by_photo.get(photo_id, (None, None))
        if row_status == processing_versions.PHOTO_VERSION_DONE and path:
            payload.append((original_name, path))
        else:
            missing.append(original_name)
    if missing and not export.allow_partial:
        raise ValueError("selected AI version is missing outputs: " + ", ".join(missing[:10]))
    if not payload:
        raise ValueError("selected AI version has no successful outputs")
    return payload


def process_photos_job(job_id: str) -> int:
    job_uuid = UUID(job_id)

    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_uuid)
        if job is None:
            raise ValueError(f"processing job {job_id} not found")

        job.status = ProcessingJobStatus.RUNNING
        job.progress = 0
        job.error = None
        db.commit()

        photo_ids = list(job.photo_ids or [])
        job.total = len(photo_ids)
        db.commit()

        failures: list[str] = []
        try:
            for photo_id in photo_ids:
                photo = db.get(Photo, photo_id)
                if photo is None:
                    failures.append(f"photo {photo_id} not found")
                    job.progress += 1
                    db.commit()
                    continue

                try:
                    result = photo_processor.process_photo(
                        project_id=job.project_id,
                        photo_id=photo.id,
                        source_relative_path=photo.stored_path,
                        preset=job.preset,
                        denoise_strength=job.denoise_strength,
                        lens_distort_correct=job.lens_distort_correct,
                        level_correct_on=job.level_correct,
                        auto_crop_aspect=job.auto_crop_aspect,
                        cpl_strength=job.cpl_strength,
                        version_number=job.version_number,
                    )
                    row = _photo_processing_version(db, job, photo.id)
                    row.status = processing_versions.PHOTO_VERSION_DONE
                    row.path = result.relative_path
                    row.error = None
                    db.add(row)
                    job.progress += 1
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()
                        written = settings.storage_root / result.relative_path
                        written.unlink(missing_ok=True)
                        raise
                except Exception as exc:
                    failures.append(f"{photo.original_filename}: {exc}")
                    row = _photo_processing_version(db, job, photo.id)
                    row.status = processing_versions.PHOTO_VERSION_FAILED
                    row.path = None
                    row.error = str(exc)
                    db.add(row)
                    job.progress += 1
                    db.commit()

            job.status = ProcessingJobStatus.FAILED if failures else ProcessingJobStatus.DONE
            job.error = "\n".join(failures[:10]) if failures else None
            job.completed_at = datetime.now(tz=timezone.utc)
            processing_versions.update_latest_processed_cache_for_job(db, job)
            db.commit()
            return job.progress
        except Exception as exc:
            job.status = ProcessingJobStatus.FAILED
            job.error = str(exc)
            job.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            raise


def _photo_processing_version(
    db,
    job: ProcessingJob,
    photo_id: UUID,
) -> PhotoProcessingVersion:
    row = db.execute(
        select(PhotoProcessingVersion).where(
            PhotoProcessingVersion.processing_job_id == job.id,
            PhotoProcessingVersion.photo_id == photo_id,
        )
    ).scalar_one_or_none()
    if row is not None:
        return row
    return PhotoProcessingVersion(processing_job_id=job.id, photo_id=photo_id, status="failed")


def apply_adjustments_job(job_id: str) -> int:
    job_uuid = UUID(job_id)

    with SessionLocal() as db:
        job = db.get(AdjustmentJob, job_uuid)
        if job is None:
            raise ValueError(f"adjustment job {job_id} not found")

        job.status = ProcessingJobStatus.RUNNING
        job.progress = 0
        job.error = None
        db.commit()

        photo_ids = list(job.photo_ids or [])
        job.total = len(photo_ids)
        db.commit()

        try:
            base_params = dict(job.params or {})
            sources = base_params.pop("_sources", {})
            for photo_id in photo_ids:
                photo = db.get(Photo, photo_id)
                if photo is None:
                    job.progress += 1
                    db.commit()
                    continue
                params = dict(base_params)
                source = sources.get(str(photo_id)) if isinstance(sources, dict) else None
                if isinstance(source, dict):
                    params["source"] = source
                adjustment_renderer.apply_to_photo(db, photo, params)
                job.progress += 1
                db.commit()

            job.status = ProcessingJobStatus.DONE
            job.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            return job.progress
        except Exception as exc:
            job.status = ProcessingJobStatus.FAILED
            job.error = str(exc)
            job.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            raise
