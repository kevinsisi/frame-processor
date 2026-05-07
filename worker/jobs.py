"""RQ job 函數。

- ``zip_export_job``: v0.1 起，把某 project 的原圖打包 zip。
- ``processing_job``: v0.2.0 起，跑色調 preset + 水平校正 + 自動裁剪 pipeline。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from api.database import SessionLocal
from models.enums import ExportStatus, ProcessingJobStatus
from models.export import Export
from models.photo import Photo
from models.processing_job import ProcessingJob
from services import photo_processor, zip_export


def zip_export_job(export_id: str) -> str:
    """打包某個 export 的所有原圖到 zip。回傳 zip 的 storage-relative path。"""

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
                    select(Photo.original_filename, Photo.stored_path).where(
                        Photo.project_id == export.project_id
                    )
                )
                .tuples()
                .all()
            )
            zip_abs = zip_export.build_zip(
                export_id=export_uuid,
                photos=[(name, path) for name, path in photos],
            )
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


def processing_job(job_id: str, photo_id_strs: list[str] | None = None) -> str:
    """對 ProcessingJob 內的照片跑 pipeline。

    ``photo_id_strs`` 為空代表處理 project 內全部 photos。
    單張失敗不殺整 job，而是計入 ``error`` 累計訊息；最後若全部失敗才 mark FAILED。
    """

    job_uuid = UUID(job_id)
    target_uuids = [UUID(s) for s in (photo_id_strs or [])]

    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_uuid)
        if job is None:
            raise ValueError(f"processing job {job_id} not found")

        if target_uuids:
            photos = (
                db.execute(
                    select(Photo)
                    .where(Photo.project_id == job.project_id)
                    .where(Photo.id.in_(target_uuids))
                )
                .scalars()
                .all()
            )
        else:
            photos = (
                db.execute(select(Photo).where(Photo.project_id == job.project_id))
                .scalars()
                .all()
            )

        job.status = ProcessingJobStatus.RUNNING
        job.progress_total = len(photos)
        job.progress_done = 0
        db.commit()

        errors: list[str] = []
        for photo in photos:
            try:
                result = photo_processor.process_photo(
                    project_id=photo.project_id,
                    photo_id=photo.id,
                    source_relative=photo.stored_path,
                    preset=job.preset,
                    apply_level_correct=job.level_correct,
                    target_aspect=job.auto_crop_aspect,
                )
                # 重新讀 photo（避免 stale），更新 processed_paths
                fresh = db.get(Photo, photo.id)
                if fresh is not None:
                    paths = dict(fresh.processed_paths or {})
                    paths[job.preset.value] = str(result.relative_path).replace("\\", "/")
                    fresh.processed_paths = paths
                    flag_modified(fresh, "processed_paths")
                job.progress_done += 1
                db.commit()
            except Exception as exc:
                errors.append(f"{photo.id}: {exc}")
                db.rollback()
                job.progress_done += 1
                db.commit()

        if errors and len(errors) == len(photos):
            job.status = ProcessingJobStatus.FAILED
        else:
            job.status = ProcessingJobStatus.DONE
        job.error = "\n".join(errors) if errors else None
        job.completed_at = datetime.now(tz=timezone.utc)
        db.commit()

        return job.status.value
