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
    gemini_model: str = "gemini-2.0-flash"

    # Model weight cache directories (mounted as Docker volumes in deploy)
    ultralytics_dir: Path = Path("./data/models-weights/ultralytics")
    nafnet_dir: Path = Path("./data/models-weights/nafnet")

    # Pipeline tuning
    nafnet_tile_size: int = 512  # CPU 推理時切 tile 避免 OOM
    lens_distort_k1: float = -0.08  # 預設輕度桶形矯正
    lens_distort_k2: float = 0.02

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
