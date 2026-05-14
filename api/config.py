from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://frame:frame@localhost:5432/frame_processor"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: Path = Path("./data")
    allowed_origins: str = "http://localhost:5173"

    # AI integrations
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    settings_admin_token: str | None = None
    key_manager_url: str | None = None

    # Model weight cache directories (mounted as Docker volumes in deploy)
    ultralytics_dir: Path = Path("./data/models-weights/ultralytics")
    nafnet_dir: Path = Path("./data/models-weights/nafnet")

    # RQ job timeouts (seconds)
    rq_job_timeout_ai_batch: int = 1800
    rq_job_timeout_adjustment_apply: int = 600
    rq_job_timeout_zip_export: int = 600

    # Pipeline tuning
    nafnet_tile_size: int = 512  # CPU 推理時切 tile 避免 OOM
    lens_distort_k1: float = -0.16  # 通用手機廣角桶形矯正
    lens_distort_k2: float = 0.04

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
