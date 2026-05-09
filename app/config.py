from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "sqlite:///./data/analytics.db"


@dataclass(frozen=True)
class Settings:
    survey_service_url: str
    internal_api_key: str
    database_url: str

    @property
    def database_path(self) -> Path:
        return resolve_database_path(self.database_url)


def resolve_database_path(database_url: str) -> Path:
    if database_url.startswith("sqlite:///"):
        raw_path = database_url.removeprefix("sqlite:///")
    else:
        raw_path = database_url

    path = Path(raw_path)
    if not path.is_absolute():
        path = BASE_DIR / path

    return path.resolve()


def get_settings() -> Settings:
    return Settings(
        survey_service_url=os.getenv("SURVEY_SERVICE_URL", "http://localhost:8081"),
        internal_api_key=os.getenv("INTERNAL_API_KEY", "change-me"),
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )
