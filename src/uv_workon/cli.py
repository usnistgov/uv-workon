"""
Console script (:mod:`~uv_workon.cli`)
======================================
"""

from __future__ import annotations

import itertools
import logging
import sys
from collections.abc import Iterator  # noqa: TC003
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

import click
import typer

from .core import (
    VirtualEnvPathAndLink,
    generate_shell_config,
    get_invalid_symlinks,
    get_virtualenv_paths,
    is_fish_shell,
    uv_run,
)
from .kernels import complete_kernelspec_names
from .utils import select_option
from .validate import (
    infer_virtualenv_name,
    infer_virtualenv_path_raise,
    validate_is_virtualenv,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TypeVar

    R = TypeVar("R")


# * Logging -------------------------------------------------------------------
FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger(__name__)


# * Utils ---------------------------------------------------------------------
def _get_input_paths(
    paths: list[Path] | None, parents: list[Path] | None
) -> Iterable[Path]:
    if paths is None:
        paths = []
    if parents is None:
        parents = []
    return itertools.chain(paths, *[p.glob("*") for p in parents])


def _select_virtualenv_path(
    venv_path: Path | None,
    venv_name: str | None,
    workon_home: Path,
    venv_patterns: list[str],
    resolve: bool = False,
) -> Path:
    if venv_path:
        path = infer_virtualenv_path_raise(
            venv_path,
            venv_patterns,
        )
    elif venv_name:
        path = validate_is_virtualenv(workon_home / venv_name)

    elif options := [p.name for p in get_virtualenv_paths(workon_home)]:
        path = workon_home / select_option(options, title="venv")
    else:  # pragma: no cover
        typer.echo("No virtual environment found")
        raise typer.Exit(0)

    if resolve:
        path = path.resolve()
    return path


def _get_venv_name_path_mapping(
    include_workon_home: bool,
    venv_names: Iterable[str] | None,
    venv_paths: Iterable[Path] | None,
    workon_home: Path,
    venv_patterns: list[str],
) -> dict[str, Path]:
    name_mapping: dict[str, Path] = {}
    if include_workon_home:
        name_mapping.update({p.name: p for p in get_virtualenv_paths(workon_home)})

    if venv_names:
        name_mapping.update(
            {name: validate_is_virtualenv(workon_home / name) for name in venv_names}
        )

    if venv_paths:
        for p in venv_paths:
            path = infer_virtualenv_path_raise(p, venv_patterns)
            name_mapping[infer_virtualenv_name(path, venv_patterns)] = path

    return name_mapping


def _confirm_action(yes: bool | None, msg: str) -> bool:
    if yes is None:
        return typer.confirm(msg)
    return yes


# * Callbacks -----------------------------------------------------------------
def _callback_expand_user(x: Path) -> Path:
    return x.expanduser()


def _callback_venv_patterns(
    ctx: typer.Context,
    venv_patterns: list[str],
) -> list[str]:
    use_default = cast("bool", ctx.params.get("use_default_venv_patterns"))
    return list({*venv_patterns, *((".venv", "venv") if use_default else ())})


def _callback_verbose(
    verbose: int | None,
) -> int | None:
    if verbose is None:
        return verbose

    if verbose < 0:  # pragma: no cover
        level = logging.ERROR
    elif not verbose:  # pragma: no cover
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:  # pragma: no cover
        level = logging.DEBUG

    for _logger in map(logging.getLogger, logging.root.manager.loggerDict):  # pylint: disable=no-member
        _logger.setLevel(level)
    return verbose


# * Completions ---------------------------------------------------------------
@lru_cache
def _all_virtualenv_names(workon_home: Path) -> list[str]:
    return [p.name for p in get_virtualenv_paths(workon_home)]


def _complete_virtualenv_names(ctx: typer.Context, incomplete: str) -> Iterator[str]:
    workon_home = ctx.params.get("workon_home")
    valid_names = _all_virtualenv_names(workon_home)
    yield from (name for name in valid_names if name.startswith(incomplete))


# this is necessary because typer has a bug where any path typed is considered
# 'complete' for arguments (even if exists=True) and a space is added to the
# end - this works around it.
def _complete_path() -> list[str]:
    return []


# * Main app ------------------------------------------------------------------
app_typer = typer.Typer()
app_kernels = typer.Typer(help="Jupyter kernel utilities")
app_typer.add_typer(app_kernels, name="kernels")


def version_callback(value: bool) -> None:
    """Versioning call back."""
    from uv_workon import __version__

    if value:
        typer.echo(f"uv-workon, version {__version__}")
        raise typer.Exit


# NOTE: have to go with this, as the magic above
# make no_arg_is_help option not work right.
@app_typer.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
) -> None:
    """Manage uv virtual environments from central location."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


# * Options -------------------------------------------------------------------
WORKON_HOME_CLI = Annotated[
    Path,
    typer.Option(
        "--workon-home",
        "-o",
        help="""
        Directory containing the virtual environments and links to virtual
        environments. If not passed, uses in order, ``WORKON_HOME`` environment
        variable, then ``~/.virtualenvs`` directory.
        """,
        envvar="WORKON_HOME",
        callback=_callback_expand_user,
        is_eager=True,  # needed for autocompletion
        autocompletion=_complete_path,
        default_factory=lambda: Path.home() / ".virtualenvs",
        show_default=False,
    ),
]
DRY_RUN_CLI = Annotated[
    bool,
    typer.Option(
        "--dry-run/--no-dry-run",
        help="Perform a dry run, without executing any action",
    ),
]
VERBOSE_CLI = Annotated[
    int | None,
    typer.Option(
        "--verbose",
        "-v",
        help="Set verbosity level.  Can specify multiple times",
        count=True,
        callback=_callback_verbose,
    ),
]
VENV_PATTERNS_CLI = Annotated[
    list[str],
    typer.Option(
        "--venv",
        help="""
        Virtual environment pattern. Can specify multiple times.
        Default is to include virtual environment directories of form
        ``".venv"`` or ``"venv"``.  To exclude these defaults, pass ``--no-default-venv``.
        """,
        envvar="UV_WORKON_VENV_PATTERNS",
        callback=_callback_venv_patterns,
        default_factory=list,
        show_default=False,
    ),
]
USE_DEFAULT_VENV_PATTERNS_CLI = Annotated[
    bool,
    typer.Option(
        "--default-venv/--no-default-venv",
        help="""
        Default is to include virtual environment patterns ``".venv"`` and ``"venv"``.
        Pass ``--no-default-venv`` to exclude these default values.
        """,
        is_eager=True,
    ),
]
RESOLVE_CLI = Annotated[
    bool,
    typer.Option(
        "--resolve/--no-resolve",
        help="""
        Pass ``--resolve`` to resolve paths and symlinks.  Otherwise, use relative paths.
        """,
    ),
]
PATHS_CLI = Annotated[
    list[Path] | None,
    typer.Argument(
        help="""
        Paths to virtual environments. These can either be full paths to
        virtual environments, or path to the parent of a virtual environment
        that has name ``venv_pattern``. If the name (the last element) of the
        path matches ``venv_pattern``, then the name of the linked virtual
        environment will come from the parent directory. Otherwise, it will be
        the name.
        """,
        autocompletion=_complete_path,
        envvar="UV_WORKON_PATHS",
    ),
]
LINK_NAMES_CLI = Annotated[
    list[str] | None,
    typer.Option(
        "--link-name",
        help="""
        Name of the linked virtual environment. Default is to infer the name
        from path. Can specify multiple times. If use this option, it must
        match up with the number of paths. It is intended to be used once only.
        Use with care in other cases.
        """,
    ),
]
PARENTS_CLI = Annotated[
    list[Path] | None,
    typer.Option(
        "--parent",
        help="""
        Parent of directories to check for ``venv_pattern`` directories
        containing virtual environments. Using ``uv-workon --parent a/path``
        is roughly equivalent to using ``uv-workon a/path/*``
        """,
        autocompletion=_complete_path,
    ),
]
YES_CLI = Annotated[
    bool | None,
    typer.Option(
        "--yes/--no",
        help="""
        Default is confirm yes/No for actions.
        Passing ``--yes`` confirms all answers as yes.
        Passing ``--no`` confirms all answers as no.
        """,
    ),
]
VENV_NAME_CLI = Annotated[
    str | None,
    typer.Option(
        "--name",
        "-n",
        help="Use virtual environment located at ${workon_home}/{name}.",
        autocompletion=_complete_virtualenv_names,
    ),
]
VENV_PATH_CLI = Annotated[
    Path | None,
    typer.Option(
        "-p",
        "--path",
        help="""Path to venv""",
        autocompletion=_complete_path,
    ),
]
UV_RUN_OPTIONS_CLI = Annotated[
    list[str], typer.Argument(help="Arguments and options passed to ``uv run ...``")
]
NO_COMMAND_CLI = Annotated[
    bool,
    typer.Option(
        "--command/--no-command",
        help="""
        If ``--command``, include command name with output.
        If ``--no-command``, only list the path.
        """,
    ),
]
# Multiple names/paths
VENV_NAMES_CLI = Annotated[
    list[str] | None,
    typer.Option(
        "-n",
        "--name",
        help="Virtual environment names.",
        autocompletion=_complete_virtualenv_names,
    ),
]
VENV_PATHS_CLI = Annotated[
    list[Path] | None,
    typer.Option(
        "-p",
        "--path",
        help="Virtual environment paths.",
        autocompletion=_complete_path,
    ),
]
SHELL_TYPE_CLI = Annotated[
    str,
    typer.Option("--shell", help="Shell type.  Right now support bash/zsh and fish"),
]


# * Commands ------------------------------------------------------------------
# ** Links
@app_typer.command("link")
def link_virtualenvs_to_workon_home(
    *,
    paths: PATHS_CLI = None,
    parents: PARENTS_CLI = None,
    link_names: LINK_NAMES_CLI = None,
    resolve: RESOLVE_CLI = False,
    workon_home: WORKON_HOME_CLI,
    venv_patterns: VENV_PATTERNS_CLI,
    use_default_venv_patterns: USE_DEFAULT_VENV_PATTERNS_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
    yes: YES_CLI = None,
) -> None:
    """Create symlink from paths to workon_home."""
    if not (input_paths := list(_get_input_paths(paths, parents))):
        with click.get_current_context() as ctx:
            typer.echo(ctx.get_help())
            sys.exit(2)

    logger.debug("params: %s", locals())

    objs = list(
        VirtualEnvPathAndLink.from_paths_and_workon(
            input_paths,
            workon_home=workon_home,
            venv_patterns=venv_patterns,
            names=link_names,
        )
    )

    for obj in objs:
        if (not obj.link.exists()) or (
            obj.link.is_symlink() and _confirm_action(yes, f"Overwrite {obj.link}")
        ):
            obj.create_symlink(resolve=resolve, dry_run=dry_run)
        else:
            logger.debug("Skipping: %s -> %s", obj.link, obj.path)


@app_typer.command("list")
def list_virtualenvs(
    *,
    workon_home: WORKON_HOME_CLI,
    verbose: VERBOSE_CLI = None,
) -> None:
    """List available central virtual environments"""
    venv_paths = get_virtualenv_paths(workon_home)
    logger.debug("params: %s", locals())

    for p in sorted(venv_paths, key=lambda x: x.name):
        typer.echo(f"{p.name:25}  {p.resolve()}")


@app_typer.command("clean")
def clean_virtualenvs(
    *,
    workon_home: WORKON_HOME_CLI,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
    yes: YES_CLI = None,
) -> None:
    """Remove missing broken virtual environment symlinks."""
    logger.debug("params: %s", locals())

    for path in get_invalid_symlinks(workon_home):
        if _confirm_action(yes, f"Remove {path} -> {path.readlink()}"):
            logger.info("Remove symlink: %s -> %s", path, path.readlink())
            if not dry_run:
                path.unlink()


@app_typer.command(
    "run",
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def run_with_virtualenv(
    *,
    ctx: typer.Context,
    venv_name: VENV_NAME_CLI = None,
    venv_path: VENV_PATH_CLI = None,
    resolve: RESOLVE_CLI = True,
    workon_home: WORKON_HOME_CLI,
    venv_patterns: VENV_PATTERNS_CLI,
    use_default_venv_patterns: USE_DEFAULT_VENV_PATTERNS_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
) -> None:
    """
    Run uv commands using using the named or specified virtual environment.

    For example, use ``uv-workon run -n my-env -- python ...`` is
    translated to ``uv run -p patt/to/my-env --no-project python ...``.
    If an option mirrors one of the command options (-n, etc), pass it after ``--``.
    Use ``--dry-run`` to echo the equivalent command to be run in the shell.

    Under the hood, this uses ``uv run`` with the environment variables
    ``VIRTUAL_ENV`` and ``UV_PROJECT_ENVIRONMENT`` and the option ``-p`` all
    set to the path of the virtual environment, and with the option
    ``--no-project``.
    """
    logger.info("params: %s", locals())

    if not ctx.args:
        typer.echo(ctx.get_help())
        sys.exit(2)

    path = _select_virtualenv_path(
        venv_path=venv_path,
        venv_name=venv_name,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
        resolve=resolve,
    )

    command = uv_run(path, *ctx.args, dry_run=dry_run)
    if dry_run:  # pragma: no branch
        typer.echo(command)


@app_typer.command("venv-link")
def link_workon_home_to_venv(
    *,
    venv_name: VENV_NAME_CLI = None,
    venv_path: VENV_PATH_CLI = None,
    resolve: RESOLVE_CLI = False,
    destination: Annotated[
        Path,
        typer.Argument(
            help="Path of linked virtual environment",
            show_default=".venv",
            default_factory=lambda: Path.cwd() / ".venv",
        ),
    ],
    workon_home: WORKON_HOME_CLI,
    venv_patterns: VENV_PATTERNS_CLI,
    use_default_venv_patterns: USE_DEFAULT_VENV_PATTERNS_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
    yes: YES_CLI = None,
) -> None:
    """
    Create symlink from virtual environment to a local ``.venv``

    This is, in a sense, the inverse of the ``link`` subcommand. While ``link``
    links from a virtualenv to ``workon_home``, this links from ``workon_home``
    to a local ``.venv``. This can then be used (with care) via ``uv run ...``.

    Note that this is experimental and subject to change.
    """
    if destination.exists():
        if not destination.is_symlink():
            typer.echo(f"{destination} exists and is not a virtualenv.  Exiting")
            sys.exit(1)
        elif not _confirm_action(yes, f"Overwrite {destination}?"):
            return

    path = _select_virtualenv_path(
        venv_path=venv_path,
        venv_name=venv_name,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
        resolve=resolve,
    )

    logger.info("Create symlink %s -> %s", destination, path)

    if not dry_run:
        destination.unlink(missing_ok=True)
        destination.symlink_to(path)


# ** Shell commands
@app_typer.command("shell-config")
def shell_config() -> None:
    """
    Use with ``eval "$(uv-workon shell-config)"`` or ``uv-workon shell-config | source`` for fish shell.

    This will add the subcommand ``uv-workon activate`` and ``uv-workon cd`` to the shell.  Without
    running shell config, ``activate`` and ``cd`` will just print the command to screen.
    """
    typer.echo(generate_shell_config())


@app_typer.command("activate")
def shell_activate(
    *,
    venv_name: VENV_NAME_CLI = None,
    venv_path: VENV_PATH_CLI = None,
    resolve: RESOLVE_CLI = False,
    no_command: NO_COMMAND_CLI = False,
    workon_home: WORKON_HOME_CLI,
    venv_patterns: VENV_PATTERNS_CLI,
    use_default_venv_patterns: USE_DEFAULT_VENV_PATTERNS_CLI = True,
) -> None:
    """Use to activate virtual environments."""
    path = _select_virtualenv_path(
        venv_path=venv_path,
        venv_name=venv_name,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
        resolve=resolve,
    )

    activate_script_name = "activate.fish" if is_fish_shell() else "activate"

    if (activate := path / "bin" / activate_script_name).exists() or (
        activate := path / "Scripts" / activate_script_name
    ).exists():
        typer.echo(str(activate) if no_command else f"source {activate}")
    else:
        logger.error("No activate script found for path %s", path)
        raise typer.Exit(1)


@app_typer.command("cd")
def shell_cd(
    *,
    venv_name: VENV_NAME_CLI = None,
    venv_path: VENV_PATH_CLI = None,
    no_command: NO_COMMAND_CLI = False,
    workon_home: WORKON_HOME_CLI,
    venv_patterns: VENV_PATTERNS_CLI,
    use_default_venv_patterns: USE_DEFAULT_VENV_PATTERNS_CLI = True,
) -> None:
    """Command to change to parent directory of virtual environment."""
    path = _select_virtualenv_path(
        venv_path=venv_path,
        venv_name=venv_name,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
        resolve=True,
    ).parent

    typer.echo(str(path) if no_command else f"cd {path}")


# ** Kernels
@app_kernels.command("install")
def install_ipykernels(
    ctx: typer.Context,
    *,
    venv_names: VENV_NAMES_CLI = None,
    venv_paths: VENV_PATHS_CLI = None,
    all_venvs: Annotated[
        bool, typer.Option("--all", help="If passed, install for all environments")
    ] = False,
    display_format: Annotated[
        str,
        typer.Option(
            "--display-format",
            help="""
            Format to use in display name. Can contain ``name`` which is
            inferred from the virtual environment location.
            """,
        ),
    ] = "Python [venv: {name}]",
    no_user: Annotated[
        bool,
        typer.Option(
            "--user/--no-user",
            help="Default is to pass the ``--user`` options.  Use this to override.",
        ),
    ] = False,
    resolve: RESOLVE_CLI = True,
    workon_home: WORKON_HOME_CLI,
    venv_patterns: VENV_PATTERNS_CLI,
    use_default_venv_patterns: USE_DEFAULT_VENV_PATTERNS_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
    yes: YES_CLI = None,
) -> None:
    """Install ipykernels for virtual environment(s) that contain ``ipykernel`` module."""
    from .kernels import get_ipykernel_install_script_path, get_kernelspecs

    script = get_ipykernel_install_script_path()
    kernelspecs = get_kernelspecs()

    for name, path in _get_venv_name_path_mapping(
        all_venvs,
        venv_names=venv_names,
        venv_paths=venv_paths,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
    ).items():
        if (name not in kernelspecs) or _confirm_action(yes, f"Reinstall {name}?"):
            display_name = display_format.format(name=name)
            command = uv_run(
                path.resolve() if resolve else path,
                "python",
                script,
                *(["--dry-run"] if dry_run else []),
                *(["--verbose"] if verbose is not None and verbose > 0 else []),
                "--",
                *ctx.args,
                "--name",
                name,
                "--display-name",
                display_name,
                *([] if no_user else ["--user"]),
                dry_run=dry_run,
            )

            if dry_run:
                typer.echo(command)


@app_kernels.command("remove")
def remove_kernels(
    *,
    names: Annotated[
        list[str] | None,
        typer.Option(
            "-n",
            "--name",
            help="Kernel names to remove",
            autocompletion=complete_kernelspec_names,
        ),
    ] = None,
    venv_paths: VENV_PATHS_CLI = None,
    missing: Annotated[
        bool,
        typer.Option("--missing", help="Remove kernelspecs that are missing/broken."),
    ] = False,
    workon_home: WORKON_HOME_CLI,
    venv_patterns: VENV_PATTERNS_CLI,
    use_default_venv_patterns: USE_DEFAULT_VENV_PATTERNS_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
    yes: YES_CLI = None,
) -> None:
    """Remove installed kernels"""
    from .kernels import (
        get_broken_kernelspecs,
        get_kernelspecs,
        has_jupyter_client,
        remove_kernelspecs,
    )

    has_jupyter_client()

    to_remove = set(
        _get_venv_name_path_mapping(
            include_workon_home=False,
            venv_names=None,
            venv_paths=venv_paths,
            workon_home=workon_home,
            venv_patterns=venv_patterns,
        )
    )
    if names is not None:
        to_remove.update(set(names))

    if missing:
        to_remove.update(set(get_broken_kernelspecs()))

    to_remove = to_remove.intersection(get_kernelspecs())

    to_remove_filtered = sorted(
        name for name in to_remove if _confirm_action(yes, f"Remove {name}")
    )

    if not to_remove_filtered:
        return

    if not dry_run:
        remove_kernelspecs(to_remove_filtered)


@app_kernels.command("list")
def list_kernels() -> None:
    """List installed kernels.  Interface to jupyter kernelspec list."""
    from .kernels import has_jupyter_client

    has_jupyter_client()

    from jupyter_client.kernelspecapp import ListKernelSpecs

    ListKernelSpecs(log_level="ERROR").start()  # ty: ignore[missing-argument]
