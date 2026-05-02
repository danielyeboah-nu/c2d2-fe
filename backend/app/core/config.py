from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    # App
    app_name: str = "C2D2 API"
    version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")

    # Database — defaults to local SQLite for dev; swap in Postgres URL for production
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./c2d2.db")

    # JWT
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production-please")
    jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "168"))

    # CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    # AI — Anthropic (scoring + adversarial + OCR vision)
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # AI — OpenAI (Whisper STT)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Claude model
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # Azure Blob Storage (optional, for photo/audio uploads)
    photos_backend: str = os.getenv("PHOTOS_BACKEND", "local")
    azure_blob_connection_string: str = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")
    azure_blob_container: str = os.getenv("AZURE_BLOB_CONTAINER", "c2d2-media")
    data_local_dir: str = os.getenv("DATA_LOCAL_DIR", "data_local")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
