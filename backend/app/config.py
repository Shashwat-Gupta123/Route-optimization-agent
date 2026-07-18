"""Application configuration loader.

Loads environment variables from ``backend/.env`` and the app-wide defaults
from ``backend/db/config.json``. All file paths, scoring weights, cost factors
and API provider/env-var names are read from here so nothing is hardcoded in
the business logic.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# backend/app/config.py -> backend/app -> backend
BACKEND_DIR = Path(__file__).resolve().parents[1]
# repo root that the paths inside config.json ("backend/db/...") are relative to
REPO_ROOT = BACKEND_DIR.parent

# Load environment variables from backend/.env (never commit real keys).
load_dotenv(BACKEND_DIR / ".env")

_CONFIG_PATH = BACKEND_DIR / "db" / "config.json"


@lru_cache(maxsize=1)
def get_config() -> Dict[str, Any]:
    """Return the parsed ``config.json`` as a dict (cached)."""
    with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_data_file(key: str) -> Path:
    """Resolve a logical data file name (from config ``data_files``) to an
    absolute path on disk.

    The paths stored in ``config.json`` are relative to the repository root
    (e.g. ``backend/db/warehouse.json``); they are resolved against
    :data:`REPO_ROOT` so the app works regardless of the current working
    directory.
    """
    rel = get_config()["data_files"][key]
    candidate = (REPO_ROOT / rel).resolve()
    if candidate.exists():
        return candidate
    # Fallback: treat the last path component as a file inside backend/db.
    return (BACKEND_DIR / "db" / Path(rel).name).resolve()


def get_env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable by name."""
    return os.getenv(name, default)


# --- Azure OpenAI connection settings (matches backend/.env variable names) ---
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPEN_AI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPEN_AI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("DEPLOYEMENT_NAME", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPEN_AI_API_VERSION", "2024-12-01-preview")

# --- Server / CORS ---
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
# Vite dev server origins and production frontend domains. 
# Defaults to "*" to allow any frontend (Render, Vercel, Netlify) to connect.
cors_env = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [origin.strip() for origin in cors_env.split(",")]
