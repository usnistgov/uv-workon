"""
Core functionality (:mod:`~uv_workon.core`)
===============================================
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Container, Iterable
    from os import PathLike
    from typing import Any

logger = logging.getLogger(__name__)


def is_valid_venv(path: Path) -> bool:
    """Check if path is a valid venv"""
    return path.is_dir() and (path / "pyvenv.cfg").exists()


def find_venvs(
    *paths: PathLike[Any], venv_patterns: str | Iterable[str] = (".venv", "venv")
) -> list[Path]:
    """
    Find paths to virtual environments.

    Parameters
    ----------
    paths : path-like
        Directories to check for `venv_patterns`
    venv_patterns : str or iterable of str
        Name of virtual environment directories to search for.


    Returns
    -------
    list of Path
        Paths to virtual environments.
    """
    venv_patterns = (
        [venv_patterns] if isinstance(venv_patterns, str) else list(venv_patterns)
    )

    out: list[Path] = []
    for _p in paths:
        path = Path(_p).expanduser()
        if is_valid_venv(path):
            # already have a venv, so add it
            out.append(path)
        else:
            for pattern in venv_patterns:
                out.extend(filter(is_valid_venv, path.glob(pattern)))
    return out


def get_path_name_pairs(
    venv_paths: Iterable[Path],
    venv_patterns: Container[str],
    resolve: bool = False,
) -> Iterable[tuple[Path, str]]:
    """
    Get (path, name) pairs.

    Yields
    ------
    tuple of Path and str
    """
    for path in venv_paths:
        path_resolved = path.resolve()

        if (name := path_resolved.name) in venv_patterns:
            name = path_resolved.parent.name

        yield (path_resolved if resolve else path, name)


def create_symlinks(
    path_name_pairs: Iterable[tuple[Path, str]],
    symlink_parent: PathLike[Any] | None = None,
    force: bool = False,
    resolve: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Create symlinks with option parent location

    Parameters
    ----------
    path_name_pairs : iterable of path str pairs
        Output from :func:`get_path_name_pairs`
    symlink_parent : path-like, optional
        Where to place the symlinks.  Defaults to current directory.
    """
    symlink_parent = Path("." if symlink_parent is None else symlink_parent)

    if not symlink_parent.is_dir():
        msg = f"{symlink_parent} is not a directory.  Must create it first."
        raise ValueError(msg)

    for path, name in path_name_pairs:
        symlink_path: Path = symlink_parent / name
        path_maybe_resolved = (
            path.resolve() if resolve else os.path.relpath(path, symlink_parent)
        )

        if not symlink_path.exists(follow_symlinks=False):
            logger.info("Create symlink %s -> %s", symlink_path, path_maybe_resolved)
            if not dry_run:
                symlink_path.symlink_to(path_maybe_resolved)

        elif force:  # pylint: disable=confusing-consecutive-elif
            logger.info("Recreate symlink %s -> %s", symlink_path, path_maybe_resolved)
            if not dry_run:
                symlink_path.unlink()
                symlink_path.symlink_to(path_maybe_resolved)

        else:
            logger.info("Leave symlink %s", symlink_path)


def clean_symlinks(
    workon_home: Path,
    dry_run: bool = False,
) -> None:
    """Remove broken symlinks from workon_home"""
    for path in workon_home.glob("*"):
        if path.is_symlink() and not is_valid_venv(path):
            logger.info("Remove symlink: %s -> %s", path, path.readlink())
            if not dry_run:
                path.unlink()
        else:
            logger.info("Leaving symlink: %s", path)


def list_venv_paths(
    workon_home: Path,
) -> list[Path]:
    """Get list of venvs by name"""
    return [path for path in workon_home.glob("*") if is_valid_venv(path)]


def get_workon_script_path() -> str:
    """Get location of woorkon script."""
    from importlib.resources import files

    return str(files().joinpath("scripts", "workon.sh"))
