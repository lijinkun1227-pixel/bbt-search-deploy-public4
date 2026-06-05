from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw" / "subtitles"
DATA_STAGING = ROOT / "data" / "staging"
ENV_PATH = ROOT / "deploy" / ".env"


def load_project_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)


def get_database_url() -> str:
    load_project_env()
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set in deploy/.env")
    return url


def get_source_video_root() -> Path:
    load_project_env()
    raw = os.environ.get("SOURCE_VIDEO_ROOT", str(ROOT / "data" / "source_videos"))
    return Path(raw)
