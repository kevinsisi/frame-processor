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
from sqlalchemy.orm.attributes import flag_modified

from api.database import SessionLocal
from models.adjustment_job import AdjustmentJob
from models.enums import ExportStatus, ProcessingJobStatus
from models.export import Export
from models.photo import Photo
from models.processing_job import ProcessingJob
from services import adjustment_renderer, photo_processor, zip_export


def zip_export_job(export_id: str) -> str:
    export_uuid = UUID(export_id)

    with SessionLocal() as db:
        export = db.get(Export, export_uuid)
        if export is None:
            raise ValueError(f"export {export_id} not found")

        export.status = ExportStatus.RUNNING
        db.commit()

        try:
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

        try:
            for photo_id in photo_ids:
                photo = db.get(Photo, photo_id)
                if photo is None:
                    job.progress += 1
                    db.commit()
                    continue

                result = photo_processor.process_photo(
                    project_id=job.project_id,
                    photo_id=photo.id,
                    source_relative_path=photo.stored_path,
                    preset=job.preset,
                    denoise_strength=job.denoise_strength,
                    lens_distort_correct=job.lens_distort_correct,
                    level_correct_on=job.level_correct,
                    auto_crop_aspect=job.auto_crop_aspect,
                )
                paths = dict(photo.processed_paths or {})
                paths[result.preset.value] = result.relative_path
                photo.processed_paths = paths
                flag_modified(photo, "processed_paths")
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
