"""Configuración leída de variables de entorno (ver .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent.parent


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    # Token para el panel docente/administrador. Vacío = endpoint deshabilitado.
    admin_token: str = ""
    # Orígenes permitidos por CORS (frontend en Vercel / GitHub Pages).
    allowed_origins: tuple = ()
    # Si mongodb_uri está vacío se usa el almacén en memoria (solo desarrollo).
    mongodb_uri: str = ""
    mongodb_db: str = "cervix_sim"
    # auto | ollama | mock
    tutor_mode: str = "auto"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    tutor_timeout: float = 10.0
    tutor_max_requests: int = 10
    # Una de cada N sesiones recibe una sugerencia inexacta (control de AOR). 0 = nunca.
    inexact_every: int = 3
    frontend_dir: str = ""
    cases_file: str = str(PKG_DIR / "data" / "cases.json")
    cases_images_dir: str = str(PKG_DIR / "static_cases")

    @classmethod
    def from_env(cls) -> "Settings":
        default_front = REPO_ROOT / "frontend"
        origins = tuple(o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip())
        return cls(
            host=os.environ.get("HOST", "127.0.0.1"),
            port=_int("PORT", 8000),
            admin_token=os.environ.get("ADMIN_TOKEN", ""),
            allowed_origins=origins,
            mongodb_uri=os.environ.get("MONGODB_URI", ""),
            mongodb_db=os.environ.get("MONGODB_DB", "cervix_sim"),
            tutor_mode=os.environ.get("TUTOR_MODE", "auto").lower(),
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "llama3"),
            tutor_timeout=_float("TUTOR_TIMEOUT", 10.0),
            tutor_max_requests=_int("TUTOR_MAX_REQUESTS", 10),
            inexact_every=_int("INEXACT_EVERY", 3),
            frontend_dir=os.environ.get("FRONTEND_DIR", str(default_front) if default_front.is_dir() else ""),
        )
