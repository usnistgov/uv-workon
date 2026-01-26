"""
Core functionality (:mod:`~uv_workon.core`)
===============================================
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

import attrs

from .validate import (
    infer_virtualenv_name,
    infer_virtualenv_path,
    is_valid_virtualenv,
    validate_dir_exists,
    validate_symlink,
    validate_venv_patterns,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from ._typing import PathLike, VirtualEnvPattern
    from ._typing_compat import Self

logger: logging.Logger = logging.getLogger(__name__)


def _converter_pathlike(path: PathLike) -> Path:
    return Path(path)


def _converter_pathlike_absolute(path: PathLike) -> Path:
    return Path(path).absolute()


@attrs.define()
class VirtualEnvPathAndLink:
    """Class to handle virtual environment with link"""

    path: Path = attrs.field(converter=_converter_pathlike)
    link: Path = attrs.field(converter=_converter_pathlike_absolute)

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
    def from_paths_and_workon(
        cls,
        paths: Iterable[PathLike],
        workon_home: PathLike,
        venv_patterns: VirtualEnvPattern,
        names: str | Iterable[str] | None = None,
    ) -> Iterable[Self]:
        """Get iterable of objects from paths"""
        venv_patterns = validate_venv_patterns(venv_patterns)
        workon_home = validate_dir_exists(workon_home)

        seq: Iterable[tuple[PathLike, str | None]]

        if names is None:
            from itertools import zip_longest

            seq = zip_longest(paths, [names])
        else:
            if isinstance(names, str):
                names = [names]
            seq = zip(paths, names, strict=True)

        for path_, name_ in seq:
            if (path := infer_virtualenv_path(path_, venv_patterns)) is not None:
                name = (
                    infer_virtualenv_name(path, venv_patterns)
                    if name_ is None
                    else name_
                )
                link = validate_symlink(workon_home / name)
                yield cls(path=path, link=link)  # pyrefly: ignore[unexpected-keyword]


def get_invalid_symlinks(workon_home: Path) -> Iterator[Path]:
    """Get iterator of paths to invalid symlinks under a given path"""
    for path in workon_home.glob("*"):
        if path.is_symlink() and not is_valid_virtualenv(path):
            yield path


def get_virtualenv_paths(
    workon_home: Path,
) -> Iterator[Path]:
    """Get iterator of virtual environment paths under a given path."""
    return (path for path in workon_home.glob("*") if is_valid_virtualenv(path))


def uv_run(
    venv_path: Path,
    *args: str,
    dry_run: bool = False,
) -> str:
    """Construct and run command under uv"""
    import shlex

    args = ("uv", "run", "-p", str(venv_path), "--no-project", *args)
    command: str = (
        f"VIRTUAL_ENV={venv_path} UV_PROJECT_ENVIRONMENT={venv_path} {shlex.join(args)}"
    )

    logger.debug("command: %s", command)
    if not dry_run:
        import subprocess

        subprocess.run(
            args,
            check=True,
            env={
                **os.environ,
                "VIRTUAL_ENV": str(venv_path),
                "UV_PROJECT_ENVIRONMENT": str(venv_path),
            },
        )
    return command


def is_fish_shell() -> bool:
    """Whether current shell is fish shell."""
    import shellingham  # pyright: ignore[reportMissingTypeStubs]

    try:
        shell_name, _ = cast("tuple[str, str]", shellingham.detect_shell())  # pyright: ignore[reportUnknownMemberType]
    except shellingham.ShellDetectionFailure:  # pragma: no cover
        shell_name = "bash"

    return shell_name == "fish"


def generate_shell_config() -> str:
    """Generate bash/zsh file for shell config."""
    from textwrap import dedent

    if is_fish_shell():
        return dedent("""
        function _uv-workon-interface
            if [ (count $argv) -gt 1 ]
                set opt $argv[2]
            else
                set opt __missing__
            end

            switch $opt
                case --help -h
                    command uv-workon $argv
                case '*'
                    command uv-workon $argv | source
            end
        end


        function uv-workon
            if [ (count $argv) -gt 0 ]
                set cmd $argv[1]
            else
                set cmd __missing__
            end

            switch $cmd
                case activate cd
                    _uv-workon-interface $argv
                case '*'
                    command uv-workon $argv
            end
        end
        """)

    return dedent("""\
    _uv-workon-interface() {
        local opt="${2-__missing__}"
        case "$opt" in
            --help | -h) command uv-workon $@ ;;
            *) eval $(command uv-workon $@) ;;
        esac
    }

    uv-workon() {
        local cmd="${1-__missing__}"
        case "$cmd" in
            activate | cd) _uv-workon-interface $@ ;;
            *) command uv-workon $@ ;;
        esac
    }

    """)
