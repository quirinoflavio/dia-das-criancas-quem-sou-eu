"""Configuração da aplicação, carregada de variáveis de ambiente / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    image_provider: str = "fake"
    image_api_key: str = ""
    gemini_image_model: str = "gemini-2.0-flash-exp"

    room_ttl_hours: int = 24
    max_upload_mb: int = 10
    data_dir: str = "./data"

    cors_origins: str = "http://localhost:5173"

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def images_path(self) -> Path:
        p = self.data_path / "images"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def rooms_path(self) -> Path:
        p = self.data_path / "rooms"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
