from __future__ import annotations

from pathlib import Path, PurePath


def normalize_path(path: Path) -> Path:
    return Path(str(PurePath(path)).replace("//?/", ""))
