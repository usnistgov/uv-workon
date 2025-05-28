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

logger = logging.getLogger(__name__)


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

        for _path, _name in seq:
            if (path := infer_virtualenv_path(_path, venv_patterns)) is not None:
                name = (
                    infer_virtualenv_name(path, venv_patterns)
                    if _name is None
                    else _name
                )
                link = validate_symlink(workon_home / name)
                yield cls(path=path, link=link)


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
    except shellingham.ShellDetectionFailure:
        shell_name = "bash"

    return shell_name == "fish"


def generate_shell_config() -> str:
    """Generate bash/zsh file for shell config."""
    from shutil import which
    from textwrap import dedent

    exe_location = which("uvw")

    if is_fish_shell():
        return dedent(f"""
        set _UV_WORKON {exe_location}

        function _uvw-interface --inherit-variable _UV_WORKON
            if [ (count $argv) -gt 1 ]
                set opt $argv[2]
            else
                set opt __missing__
            end

            switch $opt
                case --help -h
                    $_UV_WORKON activate --help
                case '*'
                    command $_UV_WORKON $argv | source
            end
        end


        function uvw --inherit-variable _UV_WORKON
            if [ (count $argv) -gt 0 ]
                set cmd $argv[1]
            else
                set cmd __missing__
            end

            switch $cmd
                case activate cd
                    _uvw-interface $argv
                case '*'
                    command $_UV_WORKON $argv
            end
        end
        """)

    return dedent(f"""\
    _UV_WORKON={exe_location}

    _uvw-interface() {{
        local opt="${{2-__missing__}}"
        case "$opt" in
            --help | -h) $_UV_WORKON activate --help ;;
            *) eval $(command $_UV_WORKON $@) ;;
        esac
    }}

    uvw() {{
        local cmd="${{1-__missing__}}"
        case "$cmd" in
            activate | cd) _uvw-interface $@ ;;
            *) command $_UV_WORKON $@ ;;
        esac
    }}

    """)
