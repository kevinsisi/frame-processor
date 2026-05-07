"""RQ job 函數。

walking skeleton 階段只有 ``zip_export``。v0.2+ 會加入照片處理 pipeline 的 job。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from api.database import SessionLocal
from models.enums import ExportStatus
from models.export import Export
from models.photo import Photo
from services import zip_export


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
        except Exception as exc:  # noqa: BLE001
            export.status = ExportStatus.FAILED
            export.error = str(exc)
            export.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            raise
