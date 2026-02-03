from __future__ import annotations

from pathlib import Path


def normalize_path(path: Path) -> Path:
    return Path(str(path).lstrip("\\?"))
