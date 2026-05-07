"""把專案內所有原圖打包成 zip。worker job 入口。"""

from __future__ import annotations

import uuid
import zipfile
from collections import Counter
from pathlib import Path

from api.config import settings


def build_zip(*, export_id: uuid.UUID, photos: list[tuple[str, str]]) -> Path:
    """寫出 <storage_root>/exports/<export_id>.zip 並回傳 absolute path。

    photos: list of (original_filename, stored_path_relative_to_storage_root)
    """

    exports_dir = settings.storage_root / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    zip_abs = exports_dir / f"{export_id}.zip"

    name_counts: Counter[str] = Counter()

    with zipfile.ZipFile(zip_abs, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for original_name, stored_relative in photos:
            src = settings.storage_root / stored_relative
            if not src.exists():
                continue
            arcname = _disambiguate(original_name, name_counts)
            zf.write(src, arcname=arcname)

    return zip_abs


def _disambiguate(name: str, counts: Counter[str]) -> str:
    counts[name] += 1
    if counts[name] == 1:
        return name
    stem = Path(name).stem
    suffix = Path(name).suffix
    return f"{stem} ({counts[name] - 1}){suffix}"


def relative_to_storage(zip_abs: Path) -> str:
    return str(zip_abs.relative_to(settings.storage_root))
