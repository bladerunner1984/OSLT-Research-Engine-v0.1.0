from __future__ import annotations

import os
from pathlib import Path


def repository_root() -> Path:
    configured = os.getenv("OSLT_ROOT")
    if configured:
        return Path(configured).resolve()
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").exists():
        return candidate
    return Path.cwd().resolve()


def database_path() -> Path:
    url = os.getenv("OSLT_DATABASE_URL", "sqlite:///runtime/oslt.db")
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError("Initial implementation supports sqlite:/// URLs only")
    raw = url[len(prefix) :]
    path = Path(raw)
    if not path.is_absolute():
        path = repository_root() / path
    return path
