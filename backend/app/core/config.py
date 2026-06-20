from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "SistemaDeSenhas"
API_PREFIX = "/api"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8777
SESSION_TTL_MINUTES = int(os.getenv("SDS_SESSION_TTL_MINUTES", "30"))

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_data_dir() -> Path:
    configured = os.getenv("SDS_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME

    return Path.home() / f".{APP_NAME.lower()}"


def get_vault_path() -> Path:
    return get_data_dir() / "vault.senhas"


def get_frontend_dist() -> Path:
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS"))
        return meipass / "frontend" / "dist"

    return PROJECT_ROOT / "frontend" / "dist"
