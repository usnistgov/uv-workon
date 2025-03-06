"""
Core functionality (:mod:`~uv_workon.core`)
===============================================
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import attrs

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any

    from ._typing import VirtualEnvPattern
    from ._typing_compat import Self

logger = logging.getLogger(__name__)


class NoVirtualEnvError(ValueError):
    """Error to raise if no virtual environment found."""


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


def is_valid_venv(path: Path) -> bool:
    """Check if path is a valid venv"""
    return path.is_dir() and (path / "pyvenv.cfg").exists()


def validate_is_venv(path: os.PathLike[Any]) -> Path:
    """Validate is a virtual environment path"""
    path = Path(path)
    if not is_valid_venv(path):
        msg = f"{path} is not a valid virtual environment"
        raise NoVirtualEnvError(msg)
    return path


def infer_virtualenv_name(path: Path, venv_patterns: VirtualEnvPattern) -> str:
    """Infer a virtual environment name from path."""
    path_resolved = path.resolve()
    if (name := path_resolved.name) in validate_venv_patterns(venv_patterns):
        return path_resolved.parent.name
    return name


def infer_virtualenv_path(
    path: os.PathLike[Any], venv_patterns: VirtualEnvPattern
) -> Path:
    """Find a virtual env by pattern."""
    path = Path(path)
    if is_valid_venv(path):
        return path

    for pattern in validate_venv_patterns(venv_patterns):
        if is_valid_venv(path_pattern := path / pattern):
            return path_pattern

    msg = f"No venv found at {path}"
    raise NoVirtualEnvError(msg)


def validate_dir_exists(path: os.PathLike[Any]) -> Path:
    """Validate that path is a directory."""
    path = Path(path)
    if not path.is_dir():
        msg = f"{path} is not a directory."
        raise ValueError(msg)
    return path


def validate_symlink(path: os.PathLike[Any]) -> Path:
    """If path exists, assert it is a symlink"""
    path = Path(path)
    if path.exists() and not path.is_symlink():
        msg = f"{path} is not a symlink"
        raise ValueError(msg)
    return path


def _converter_pathlike(path: str | os.PathLike[Any]) -> Path:
    return Path(path)


def _converter_pathlike_absolute(path: str | os.PathLike[Any]) -> Path:
    return Path(path).absolute()


@attrs.define()
class VirtualEnvPath:
    """Class to handle virtual environment path."""

    path: Path = attrs.field(converter=_converter_pathlike)

    def is_valid_path(self) -> bool:
        """Check if path is a valid virtual environment"""
        return is_valid_venv(self.path)

    def resolve(self) -> Self:
        """Create new object with resolved path."""
        return attrs.evolve(self, path=self.path.resolve())

    @classmethod
    def from_path(
        cls, path: os.PathLike[Any], venv_patterns: VirtualEnvPattern
    ) -> Self:
        """Create object from path."""
        return cls(infer_virtualenv_path(path, validate_venv_patterns(venv_patterns)))


@attrs.define()
class VirtualEnvPathAndLink(VirtualEnvPath):
    """Class to handle virtual environment with link"""

    link: Path = attrs.field(converter=_converter_pathlike_absolute)

    def is_valid_link(self) -> bool:
        """Whether link does not exist or is a symlink"""
        return (not self.link.exists()) or self.path.is_symlink()

    def create_symlink(
        self,
        resolve: bool = False,
        dry_run: bool = False,
    ) -> None:
        """Create the symlink."""
        path = (
            self.path.resolve()
            if resolve
            else os.path.relpath(self.path.absolute(), self.link.parent)
        )
        logger.info("Creating symlink %s -> %s", self.link, path)
        if not dry_run:
            self.link.unlink(missing_ok=True)
            self.link.symlink_to(path)

    @classmethod
    def from_path_and_workon(
        cls,
        path: os.PathLike[Any],
        workon_home: os.PathLike[Any],
        name: str | None,
        venv_patterns: VirtualEnvPattern,
    ) -> Self:
        """Create a (path, link) pair."""
        venv_patterns = validate_venv_patterns(venv_patterns)
        path = infer_virtualenv_path(path, venv_patterns)
        if name is None:
            name = infer_virtualenv_name(path, venv_patterns)
        return cls(path=path, link=validate_dir_exists(workon_home) / name)

    @classmethod
    def from_paths_and_workon(
        cls,
        paths: Iterable[os.PathLike[Any]],
        workon_home: os.PathLike[Any],
        venv_patterns: VirtualEnvPattern,
    ) -> Iterable[Self]:
        """Get iterable of objects."""
        venv_patterns = validate_venv_patterns(venv_patterns)
        workon_home = validate_dir_exists(workon_home)

        for _path in paths:
            try:
                path = infer_virtualenv_path(_path, venv_patterns)
            except NoVirtualEnvError:
                continue

            name = infer_virtualenv_name(path, venv_patterns)
            link = validate_symlink(workon_home / name)

            yield cls(path=path, link=link)


def get_invalid_symlinks(workon_home: Path) -> Iterable[Path]:
    """Get Iterable of paths to invalid symlinks."""
    for path in workon_home.glob("*"):
        if path.is_symlink() and not is_valid_venv(path):
            yield path


def list_venv_paths(
    workon_home: Path,
) -> list[Path]:
    """Get list of venvs by name"""
    return [path for path in workon_home.glob("*") if is_valid_venv(path)]


def select_option(
    options: Sequence[str],
    title: str = "",
    usage: bool = True,
) -> str:
    """Use selector"""
    from simple_term_menu import (  # pyright: ignore[reportMissingTypeStubs]
        TerminalMenu,
    )

    title = " ".join(
        [
            *([title] if title else []),
            *(
                ["use arrows or j/k to move down/up, or / to limit by name"]
                if usage
                else []
            ),
        ]
    )
    index: int = TerminalMenu(options, title=title or None).show()  # pyright: ignore[reportAssignmentType]
    return options[index]


def generate_shell_config() -> str:
    """Generate bash/zsh file for shell config."""
    from shutil import which
    from textwrap import dedent

    exe_location = which("uv-workon")

    return dedent(f"""\
    __UV_WORKON={exe_location}

    __uv-workon-activate() {{
        local cmd="${{1-__missing__}}"
        case "$cmd" in
            --help | -h) $__UV_WORKON shell-activate --help ;;
            *) source $(command $__UV_WORKON shell-activate $@) ;;
        esac
    }}

    uv-workon() {{
        local cmd="${{1-__missing__}}"
        if [[ "$cmd" == "activate" ]]; then
            shift
            __uv-workon-activate $@
        else
            command uv-workon $@
        fi
    }}

    alias uvw=uv-workon
    """)
