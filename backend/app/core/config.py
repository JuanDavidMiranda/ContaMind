from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "ContaMind AI"
    database_url: str = "postgresql+psycopg://contamind:contamind@localhost:5432/contamind"
    storage_dir: Path = Path("storage")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    max_rows_per_file: int = Field(default=10_000, ge=1)
    cors_origins: str = "http://localhost:3000"
    dev_user_email: str = "dev@contamind.local"
    dev_user_name: str = "Usuario local de desarrollo"
    monetary_tolerance: str = "0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def resolved_storage_dir(self) -> Path:
        path = self.storage_dir
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[3] / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
