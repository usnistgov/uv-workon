"""
Console script (:mod:`~uv_workon.cli`)
==========================================================
"""

from __future__ import annotations

import argparse
import itertools
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .core import (
    clean_symlinks,
    create_symlinks,
    find_venvs,
    get_path_name_pairs,
    get_workon_script_path,
    is_valid_venv,
    list_venv_paths,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any

    class _Parser:
        """Typing interface to parser."""

        command: str | None
        venv: list[str]
        no_default_venv: bool
        paths: list[Path]
        parent: list[Path]
        workon_home: Path | None
        force: bool
        resolve: bool
        verbose: int
        dry_run: bool
        full_path: bool
        name: str | None
        uv_options: str
        run_path: Path | None


# * Logging
FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger(__name__)


# * Options


def get_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    """Get base parser."""
    # parent/shared parsers
    shared_parent_parser = argparse.ArgumentParser(add_help=False)
    shared_parent_parser.add_argument(
        "--workon-home",
        "-o",
        type=Path,
        default=None,
        help="""
        Directory containing the virtual environments and links to virtual
        environments. If not passed, uses in order, `WORKON_HOME` environment
        variable, then `~/.virtualenvs` directory.
        """,
    )
    shared_parent_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run, without executing any action",
    )
    shared_parent_parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set verbosity level.  Can specify multiple times",
    )

    resolve_parent_parser = argparse.ArgumentParser(add_help=False)
    resolve_parent_parser.add_argument(
        "--resolve",
        action="store_true",
        help="Pass this option to use absolute paths.  Default is to use relative paths.",
    )

    venvs_parent_parser = argparse.ArgumentParser(add_help=False)
    venvs_parent_parser.add_argument(
        "--venv",
        type=str,
        default=[],
        action="append",
        help="""
        Virtual environment pattern. Can specify multiple times.
        Default is to include virtual environment directories of form
        `.venv` or `venv`.  To exclude these defaults, pass `--no-default-venv`.
        """,
    )
    venvs_parent_parser.add_argument(
        "--no-default-venv",
        action="store_true",
        help="""
        Default is to include virtual environment patterns `.venv` and `venv`.
        Pass `--no-default-venv` to exclude these default values.
        """,
    )

    # Main parsers
    parser = argparse.ArgumentParser(
        description="Program to work with centralized virtual environments",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_get_version_string()}"
    )

    subparsers = parser.add_subparsers(dest="command")
    parser_link = subparsers.add_parser(
        name="link",
        help="Create symlinks",
        description="Create symlinks from central location to virtual environments.",
        parents=[shared_parent_parser, resolve_parent_parser, venvs_parent_parser],
    )
    parser_clean = subparsers.add_parser(
        name="clean",
        help="Clean symlinks",
        description="Remove broken symlinked virtual environments",
        parents=[shared_parent_parser],
    )
    parser_list = subparsers.add_parser(
        name="list",
        help="List venvs",
        description="List available centralized virtual environments",
        parents=[shared_parent_parser, resolve_parent_parser],
    )
    parser_script = subparsers.add_parser(
        name="script",
        help="Print path to script",
        description="To be used with `source $(uv-workon script)`",
        parents=[shared_parent_parser],
    )
    parser_run = subparsers.add_parser(
        name="uv-run",
        aliases=["run"],
        help="Run commands using uv run",
        description="Run uv commands using using the named or specified virtual environment.",
        epilog="""
        For example, use `symlink-venv uv-run -n my-env -- python ...` is
        translated to `uv run -p patt/to/my-env --no-project python ...`.
        """,
        parents=[shared_parent_parser, venvs_parent_parser],
    )

    subparsers_with_subcommands = {
        "link": parser_link,
        "clean": parser_clean,
        "list": parser_list,
        "script": parser_script,
    }

    parser_link.add_argument(
        "paths",
        type=Path,
        nargs="*",
        help="""
        Paths to virtual environments. These can either be full paths to
        virtual environments, or path to the parent of a virtual environment
        that has name `venv_pattern`. If the name (the last element) of the
        path matches `venv_pattern`, then the name of the linked virtual
        environment will come from the parent directory. Otherwise, it will be
        the name.
        """,
    )
    parser_link.add_argument(
        "--parent",
        type=Path,
        default=[],
        action="append",
        help="""
        Parent of directories to check for `venv_pattern` directories
        containing virtual environments. Using `uv-workon --parent a/path`
        is roughly equivalent to using `uv-workon a/path/*`
        """,
    )
    parser_link.add_argument(
        "--force",
        action="store_true",
        help="Pass this option to overwrite existing symlinks",
    )

    # list
    parser_list.add_argument(
        "--full-path",
        action="store_true",
        help="Default is to list just names.  if `--full-path`, then include full path",
    )

    # run
    parser_run.add_argument(
        "-n", "--name", type=str, default=None, help="venv name use in run"
    )
    parser_run.add_argument(
        "-p",
        "--path",
        dest="run_path",
        type=Path,
        default=None,
        help="""Path to venv""",
    )
    parser_run.add_argument(
        "uv_options",
        type=str,
        nargs="+",
        default=[],
        help="run `uv run -p {workon}/{name} --no-config {commands}`",
    )

    return parser, subparsers_with_subcommands


def set_verbosity_level(
    verbosity: int,
) -> None:
    """Set verbosity level."""
    if verbosity < 0:
        level = logging.ERROR
    elif not verbosity:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    for _logger in map(logging.getLogger, logging.root.manager.loggerDict):  # pylint: disable=no-member
        _logger.setLevel(level)


def _get_version_string() -> str:
    from . import __version__

    return __version__


def _get_venv_dir_names(
    venv_patterns: list[str], use_default: bool = True
) -> list[str]:
    if not (out := list({*venv_patterns, *((".venv", "venv") if use_default else ())})):
        msg = (
            "No venv_patterns specified.  Either pass venv_patterns or allow defaults."
        )
        raise ValueError(msg)
    return out


def _get_input_paths(paths: list[Path], parents: list[Path]) -> Iterable[Path]:
    return itertools.chain(paths, *[p.glob("*") for p in parents])


def _get_workon_home(workon_home: Path | None) -> Path:
    if workon_home is None:
        workon_home = Path(os.environ.get("WORKON_HOME", Path.home() / ".virtualenvs"))
    return workon_home.expanduser()


def _link_venvs(options: _Parser, parser: argparse.ArgumentParser) -> None:
    if not (options.parent or options.paths):
        parser.print_help()

    venv_patterns = _get_venv_dir_names(options.venv, not options.no_default_venv)
    input_paths = _get_input_paths(options.paths, options.parent)

    logger.info("venv_patterns: %s", venv_patterns)

    venv_paths = find_venvs(*input_paths, venv_patterns=venv_patterns)
    logger.info("venv_paths: %s", venv_paths)

    workon_home = _get_workon_home(options.workon_home)
    logger.info("workon_home: %s", workon_home)

    create_symlinks(
        get_path_name_pairs(
            venv_paths, resolve=options.resolve, venv_patterns=venv_patterns
        ),
        symlink_parent=workon_home,
        force=options.force,
        resolve=options.resolve,
        dry_run=options.dry_run,
    )


def _run_command(options: _Parser) -> None:
    logger.info("uv_options: %s", options.uv_options)

    if options.name:
        workon_home = _get_workon_home(options.workon_home)
        path = workon_home / options.name
        if not is_valid_venv(path):
            msg = f"{path} not a venv"
            raise ValueError(msg)

    elif options.run_path:  # pylint: disable=confusing-consecutive-elif
        venv_patterns = _get_venv_dir_names(options.venv, not options.no_default_venv)
        paths = find_venvs(options.run_path, venv_patterns=venv_patterns)
        if len(paths) == 1:
            path = paths[0]
        else:
            msg = f"No venv found at {options.run_path}"
            raise ValueError(msg)

    else:
        msg = "Must specify name or path"
        raise ValueError(msg)

    args = ["uv", "run", "-p", str(path), "--no-project", *options.uv_options]
    logger.info("running args: %s", args)
    if not options.dry_run:
        import subprocess

        subprocess.run(args, check=True)


def main(
    args: Sequence[str] | None = None,
) -> int:
    """Main cli application."""
    parser, subparsers = get_parser()

    options = cast(
        "_Parser",
        parser.parse_args() if args is None else parser.parse_args(args),
    )  # pragma: no cover

    if options.command is not None:
        set_verbosity_level(verbosity=options.verbose)
        logger.debug("cli options: %s", options)

    logger.debug("command: %s", options.command)
    if options.command == "link":
        _link_venvs(options, subparsers["link"])

    elif options.command == "clean":
        workon_home = _get_workon_home(options.workon_home)
        clean_symlinks(workon_home, options.dry_run)

    elif options.command == "list":
        workon_home = _get_workon_home(options.workon_home)
        venv_paths = list_venv_paths(workon_home)

        seq: Any
        if options.resolve:
            seq = (p.resolve() for p in venv_paths)
        elif options.full_path:
            seq = venv_paths
        else:
            seq = (p.name for p in venv_paths)

        for x in seq:
            print(x)

    elif options.command == "script":
        print(get_workon_script_path())

    elif options.command in {"uv-run", "run"}:
        _run_command(options)

    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
