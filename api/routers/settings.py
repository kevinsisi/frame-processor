from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.config import settings as app_settings
from api.database import get_db
from services.settings_store import (
    clear_gemini_api_keys,
    get_pool_summary,
    merge_gemini_api_keys,
    parse_keys_input,
    sync_from_key_manager,
)

router = APIRouter(prefix="/settings", tags=["settings"])
DbDep = Annotated[Session, Depends(get_db)]


class KeyPoolOut(BaseModel):
    count: int
    source: str
    masked_suffixes: list[str]


class SettingsOut(BaseModel):
    gemini_model: str
    key_manager_url: str
    gemini_api_keys: KeyPoolOut


class GeminiKeysUpdateIn(BaseModel):
    raw: str = Field(..., min_length=0, max_length=200_000)
    replace: bool = True


class GeminiKeysUpdateOut(BaseModel):
    stored_count: int
    accepted_count: int
    rejected_count: int


class SyncFromManagerIn(BaseModel):
    trusted_only: bool = True
    replace: bool = False


class SyncFromManagerOut(BaseModel):
    fetched: int
    imported: int
    skipped: int
    stored_count: int


def require_settings_admin(
    x_settings_token: Annotated[str | None, Header(alias="X-Settings-Token")] = None,
) -> None:
    if not app_settings.settings_admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SETTINGS_ADMIN_TOKEN is not configured",
        )
    if x_settings_token != app_settings.settings_admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid settings token",
        )


@router.get("", response_model=SettingsOut)
def get_settings(db: DbDep) -> SettingsOut:
    summary = get_pool_summary(db)
    return SettingsOut(
        gemini_model=app_settings.gemini_model,
        key_manager_url=app_settings.key_manager_url,
        gemini_api_keys=KeyPoolOut(
            count=summary.count,
            source=summary.source,
            masked_suffixes=list(summary.masked_suffixes),
        ),
    )


@router.put("/gemini-api-keys", response_model=GeminiKeysUpdateOut)
def update_gemini_api_keys(
    payload: GeminiKeysUpdateIn,
    db: DbDep,
    _admin: Annotated[None, Depends(require_settings_admin)],
) -> GeminiKeysUpdateOut:
    parsed = parse_keys_input(payload.raw)
    raw_lines = sum(
        1 for line in payload.raw.replace("\r\n", "\n").split("\n") if line.strip()
    )
    rejected = max(0, raw_lines - len(parsed))
    if raw_lines > 0 and not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no valid Gemini API keys found",
        )
    _imported, _skipped, stored = merge_gemini_api_keys(db, parsed, payload.replace)
    return GeminiKeysUpdateOut(
        stored_count=stored,
        accepted_count=len(parsed),
        rejected_count=rejected,
    )


@router.delete("/gemini-api-keys", status_code=status.HTTP_204_NO_CONTENT)
def clear_keys(db: DbDep, _admin: Annotated[None, Depends(require_settings_admin)]) -> None:
    clear_gemini_api_keys(db)


@router.post("/sync-from-key-manager", response_model=SyncFromManagerOut)
def sync_keys(
    payload: SyncFromManagerIn,
    db: DbDep,
    _admin: Annotated[None, Depends(require_settings_admin)],
) -> SyncFromManagerOut:
    try:
        result = sync_from_key_manager(
            db,
            app_settings.key_manager_url,
            trusted_only=payload.trusted_only,
            replace=payload.replace,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return SyncFromManagerOut(
        fetched=result.fetched,
        imported=result.imported,
        skipped=result.skipped,
        stored_count=result.stored_count,
    )
