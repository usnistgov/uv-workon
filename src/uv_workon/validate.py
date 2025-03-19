"""
Validation/inference (:mod:`~uv_workon.validate`)
=================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Container, Iterable

    from ._typing import PathLike, VirtualEnvPattern


class NoVirtualEnvError(ValueError):
    """Error to raise if no virtual environment found."""


# ** Validate
def validate_venv_patterns(venv_patterns: VirtualEnvPattern) -> list[str]:
    """Validate venv patterns."""
    # fast exit for most likely cas
    if isinstance(venv_patterns, list):
        return venv_patterns

    if venv_patterns is None:
        return []

    if isinstance(venv_patterns, str):
        return [venv_patterns]

    return list(venv_patterns)


def is_valid_virtualenv(path: Path) -> bool:
    """Check if path is a valid venv"""
    return path.is_dir() and (path / "pyvenv.cfg").exists()


def validate_is_virtualenv(path: PathLike) -> Path:
    """Validate is a virtual environment path"""
    path = Path(path)
    if not is_valid_virtualenv(path):
        msg = f"{path} is not a valid virtual environment"
        raise NoVirtualEnvError(msg)
    return path


def validate_dir_exists(path: PathLike) -> Path:
    """Validate that path is a directory."""
    path = Path(path)
    if not path.is_dir():
        msg = f"{path} is not a directory."
        raise ValueError(msg)
    return path


def validate_symlink(path: PathLike) -> Path:
    """If path exists, assert it is a symlink"""
    path = Path(path)
    if path.exists() and not path.is_symlink():
        msg = f"{path} exists and is not a symlink"
        raise ValueError(msg)
    return path


# ** Infer
def infer_virtualenv_name(path: Path, venv_patterns: Container[str]) -> str:
    """Infer a virtual environment name from path."""
    path_resolved = path.resolve()
    if (name := path_resolved.name) in venv_patterns:
        return path_resolved.parent.name
    return name


def infer_virtualenv_path(
    path: PathLike,
    venv_patterns: Iterable[str],
) -> Path | None:
    """Find a virtual env by pattern and return None if not found."""
    path = Path(path)
    if is_valid_virtualenv(path):
        return path
    for pattern in venv_patterns:
        if is_valid_virtualenv(path_pattern := path / pattern):
            return path_pattern
    return None


def infer_virtualenv_path_raise(
    path: PathLike,
    venv_patterns: Iterable[str],
) -> Path:
    """Find a virtual env by pattern and raise if not found."""
    if (path_ := infer_virtualenv_path(path, venv_patterns)) is None:
        msg = f"No venv found at {path}"
        raise NoVirtualEnvError(msg)
    return path_
