from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://frame:frame@localhost:5432/frame_processor"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: Path = Path("./data")
    allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
