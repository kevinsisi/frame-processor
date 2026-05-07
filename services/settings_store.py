"""DB-backed runtime settings for Gemini key management."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.config import settings
from models.app_setting import AppSetting

GEMINI_API_KEYS_KEY = "gemini_api_keys"
DEFAULT_KEY_MANAGER_URL = "http://key.sisihome.org:7823"

_GEMINI_KEY_RE = re.compile(r"^AIzaSy[0-9A-Za-z_\-]{30,40}$")


@dataclass(frozen=True)
class KeyPoolSummary:
    count: int
    source: str  # "db" | "env" | "none"
    masked_suffixes: tuple[str, ...]


@dataclass(frozen=True)
class SyncResult:
    fetched: int
    imported: int
    skipped: int
    stored_count: int


def parse_keys_input(raw: str) -> list[str]:
    if not raw:
        return []

    candidates: list[str] = []
    for raw_line in raw.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" in line:
            lhs, _, rhs = line.partition("=")
            if re.fullmatch(r"\w+", lhs.strip()):
                line = rhs.strip().strip("\"'")
        candidates.extend(part.strip() for part in line.split(",") if part.strip())

    seen: set[str] = set()
    valid: list[str] = []
    for key in candidates:
        if not _GEMINI_KEY_RE.fullmatch(key) or key in seen:
            continue
        seen.add(key)
        valid.append(key)
    return valid


def _env_keys() -> list[str]:
    raw = settings.gemini_api_key or ""
    return parse_keys_input(raw)


def _db_keys(db: Session) -> list[str]:
    value = db.execute(
        select(AppSetting.value).where(AppSetting.key == GEMINI_API_KEYS_KEY)
    ).scalar_one_or_none()
    return parse_keys_input(value or "")


def get_gemini_api_keys(db: Session) -> tuple[str, ...]:
    db_keys = _db_keys(db)
    if db_keys:
        return tuple(db_keys)
    return tuple(_env_keys())


def get_active_gemini_api_key(db: Session) -> str | None:
    keys = get_gemini_api_keys(db)
    return keys[0] if keys else None


def get_pool_summary(db: Session) -> KeyPoolSummary:
    db_keys = _db_keys(db)
    if db_keys:
        return KeyPoolSummary(
            count=len(db_keys),
            source="db",
            masked_suffixes=tuple(key[-4:] for key in db_keys),
        )
    env_keys = _env_keys()
    if env_keys:
        return KeyPoolSummary(
            count=len(env_keys),
            source="env",
            masked_suffixes=tuple(key[-4:] for key in env_keys),
        )
    return KeyPoolSummary(count=0, source="none", masked_suffixes=())


def set_gemini_api_keys(db: Session, keys: list[str]) -> int:
    deduped: list[str] = []
    seen: set[str] = set()
    for key in keys:
        key = key.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)

    stmt = pg_insert(AppSetting).values(
        key=GEMINI_API_KEYS_KEY,
        value=",".join(deduped),
        updated_at=datetime.now(UTC),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": stmt.excluded.value, "updated_at": stmt.excluded.updated_at},
    )
    db.execute(stmt)
    db.commit()
    return len(deduped)


def clear_gemini_api_keys(db: Session) -> None:
    set_gemini_api_keys(db, [])


def merge_gemini_api_keys(db: Session, incoming: list[str], replace: bool) -> tuple[int, int, int]:
    if replace:
        stored = set_gemini_api_keys(db, incoming)
        return len(incoming), 0, stored

    existing = _db_keys(db)
    seen = set(existing)
    merged = list(existing)
    imported = 0
    skipped = 0
    for key in incoming:
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        merged.append(key)
        imported += 1
    stored = set_gemini_api_keys(db, merged)
    return imported, skipped, stored


def sync_from_key_manager(
    db: Session,
    url: str = DEFAULT_KEY_MANAGER_URL,
    *,
    trusted_only: bool = True,
    replace: bool = False,
) -> SyncResult:
    base = url.rstrip("/")
    params = urllib.parse.urlencode({"trusted_only": "1"}) if trusted_only else ""
    export_url = f"{base}/api/keys/export" + (f"?{params}" if params else "")

    request = urllib.request.Request(export_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(f"key-manager returned HTTP {response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"key-manager unreachable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("key-manager returned invalid JSON") from exc

    groups = payload.get("groups") or {}
    fetched: list[str] = []
    if isinstance(groups, dict):
        for keys in groups.values():
            if isinstance(keys, list):
                fetched.extend(str(key) for key in keys)
    parsed = parse_keys_input(",".join(fetched))
    if not parsed:
        return SyncResult(fetched=0, imported=0, skipped=0, stored_count=len(_db_keys(db)))
    imported, skipped, stored = merge_gemini_api_keys(db, parsed, replace)
    return SyncResult(
        fetched=len(parsed),
        imported=imported,
        skipped=skipped,
        stored_count=stored,
    )
