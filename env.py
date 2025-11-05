from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore


def load_env() -> None:
    """Load environment variables from a .env file if python-dotenv is available.

    Search order:
    - The directory of this file (project package dir)
    - The parent directory (repo root)
    - Current working directory
    """
    if load_dotenv is None:
        return

    here = Path(__file__).resolve().parent
    candidates = [
        here / ".env",
        here.parent / ".env",
        Path(os.getcwd()) / ".env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(dotenv_path=path, override=False)
            break

# Auto-load on import
load_env()


