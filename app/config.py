from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "data" / "calculator.db"
DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5500,"
    "http://localhost:5500,"
    "http://127.0.0.1:8000,"
    "http://localhost:8000"
)


@dataclass(frozen=True)
class Settings:
    database_path: Path
    allowed_origins: tuple[str, ...]


def get_settings() -> Settings:
    raw_database_path = os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
    raw_origins = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    origins = tuple(
        origin.strip() for origin in raw_origins.split(",") if origin.strip()
    )

    if not origins:
        origins = ("http://127.0.0.1:5500",)

    return Settings(
        database_path=Path(raw_database_path).expanduser().resolve(),
        allowed_origins=origins,
    )


settings = get_settings()
