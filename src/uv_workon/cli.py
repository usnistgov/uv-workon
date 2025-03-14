"""
Console script (:mod:`~uv_workon.cli`
======================================
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Iterator  # noqa: TC003
from functools import lru_cache, wraps
from inspect import signature
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast

import click
import typer

from .core import (
    VirtualEnvPathAndLink,
    generate_shell_config,
    get_invalid_symlinks,
    infer_virtualenv_name,
    infer_virtualenv_path_raise,
    list_venv_paths,
    select_option,
    uv_run,
    validate_is_virtualenv,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import TypeVar

    R = TypeVar("R")


# * Logging -------------------------------------------------------------------
FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger(__name__)


# * Utils ---------------------------------------------------------------------
def _get_venv_dir_names(
    venv_patterns: list[str] | None, use_default: bool = True
) -> list[str]:
    if venv_patterns is None:
        venv_patterns = []

    if not (out := list({*venv_patterns, *((".venv", "venv") if use_default else ())})):
        msg = (
            "No venv_patterns specified.  Either pass venv_patterns or allow defaults."
        )
        raise ValueError(msg)
    return out


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
    venv_patterns: list[str] | None,
    use_default_venv_patterns: bool = False,
    resolve: bool = False,
) -> Path:
    if venv_path:
        path = infer_virtualenv_path_raise(
            venv_path,
            _get_venv_dir_names(venv_patterns, use_default=use_default_venv_patterns),
        )
    elif venv_name:
        path = validate_is_virtualenv(workon_home / venv_name)

    elif options := [p.name for p in list_venv_paths(workon_home)]:
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
    venv_patterns: list[str] | None,
    use_default_venv_patterns: bool,
) -> dict[str, Path]:
    name_mapping: dict[str, Path] = {}
    if include_workon_home:
        name_mapping.update({p.name: p for p in list_venv_paths(workon_home)})

    if venv_names:
        name_mapping.update(
            {name: validate_is_virtualenv(workon_home / name) for name in venv_names}
        )

    if venv_paths:
        venv_patterns = _get_venv_dir_names(
            venv_patterns, use_default=use_default_venv_patterns
        )

        for p in venv_paths:
            path = infer_virtualenv_path_raise(p, venv_patterns)
            name_mapping[infer_virtualenv_name(path, venv_patterns)] = path

    return name_mapping


def _expand_user(x: Path) -> Path:
    return x.expanduser()


# * Completions ---------------------------------------------------------------
@lru_cache
def _all_virtualenv_names(workon_home: Path) -> list[str]:
    return [p.name for p in list_venv_paths(workon_home)]


def _complete_virtualenv_names(ctx: typer.Context, incomplete: str) -> Iterator[str]:
    workon_home = ctx.params.get("workon_home")
    valid_names = _all_virtualenv_names(workon_home)
    yield from (name for name in valid_names if name.startswith(incomplete))


# this is necessary because typer has a bug
# where any path typed is considered 'complete'
# for arguments (even if exists=True) and a space
# is added to the end - this works around it.
def _complete_path() -> list[str]:  # pragma: no cover
    return []


def _complete_kernelspec_names(incomplete: str) -> Iterator[str]:
    from .kernels import get_kernelspecs

    valid_names = get_kernelspecs()
    yield from (name for name in valid_names if name.startswith(incomplete))


# * Main app ------------------------------------------------------------------
app_typer = typer.Typer(no_args_is_help=True)
app_kernels = typer.Typer(no_args_is_help=True, help="Jupyter kernel utilities")
app_typer.add_typer(app_kernels, name="kernels")


def version_callback(value: bool) -> None:
    """Versioning call back."""
    from uv_workon import __version__

    if value:
        typer.echo(f"uv-workon, version {__version__}")
        raise typer.Exit


@app_typer.callback()
def main(
    version: bool = typer.Option(  # noqa: ARG001
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
) -> None:
    """Manage uv virtual environments from central location."""
    return


# * Options -------------------------------------------------------------------

WORKON_HOME_DEFAULT = Path("~/.virtualenvs")
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
        callback=_expand_user,
        is_eager=True,  # needed for autocompletion
        autocompletion=_complete_path,
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
    ),
]
VENV_PATTERNS_CLI = Annotated[
    list[str] | None,
    typer.Option(
        "--venv",
        help="""
        Virtual environment pattern. Can specify multiple times.
        Default is to include virtual environment directories of form
        ``".venv"`` or ``"venv"``.  To exclude these defaults, pass ``--no-default-venv``.
        """,
    ),
]
USE_DEFAULT_VENV_CLI = Annotated[
    bool,
    typer.Option(
        "--default-venv/--no-default-venv",
        help="""
        Default is to include virtual environment patterns ``".venv"`` and ``"venv"``.
        Pass ``--no-default-venv`` to exclude these default values.
        """,
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
    bool,
    typer.Option(
        "--yes/--no",
        help="Answer yes to all confirmations",
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
VENV_PATHS_CLI = Annotated[
    list[Path] | None,
    typer.Option(
        "-p",
        "--path",
        help="Virtual environment paths.",
        autocompletion=_complete_path,
    ),
]


def _add_verbose_logger(
    verbose_arg: str = "verbose",
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorator factory to add logger and set logger level based on verbosity argument value."""

    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        bind = signature(func).bind

        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> R:
            params = bind(*args, **kwargs)
            params.apply_defaults()

            if (verbosity := cast("int | None", params.arguments[verbose_arg])) is None:
                # leave where it is:
                pass
            else:
                if verbosity < 0:  # pragma: no cover
                    level = logging.ERROR
                elif not verbosity:  # pragma: no cover
                    level = logging.WARNING
                elif verbosity == 1:
                    level = logging.INFO
                else:  # pragma: no cover
                    level = logging.DEBUG

                for _logger in map(logging.getLogger, logging.root.manager.loggerDict):  # pylint: disable=no-member
                    _logger.setLevel(level)

            # add error logger to function call
            try:
                return func(*args, **kwargs)
            except Exception:  # pragma: no cover
                logger.exception("found error")
                raise

        return wrapped

    return decorator


# * Commands ------------------------------------------------------------------
# NOTE: return locals() for testing purposes.
@app_typer.command("link")
@_add_verbose_logger()
def link_virtualenvs(
    paths: PATHS_CLI = None,
    parents: PARENTS_CLI = None,
    link_names: LINK_NAMES_CLI = None,
    resolve: RESOLVE_CLI = False,
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    venv_patterns: VENV_PATTERNS_CLI = None,
    use_default_venv_patterns: USE_DEFAULT_VENV_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
    yes: YES_CLI = False,
) -> None:
    """Create symlink from paths to workon_home."""
    if not (input_paths := list(_get_input_paths(paths, parents))):
        with click.get_current_context() as ctx:
            typer.echo(ctx.get_help())

    venv_patterns = _get_venv_dir_names(
        venv_patterns, use_default=use_default_venv_patterns
    )
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
            obj.link.is_symlink() and (yes or typer.confirm(f"Overwrite {obj.link}"))
        ):
            obj.create_symlink(resolve=resolve, dry_run=dry_run)
        else:
            logger.debug("Skipping: %s -> %s", obj.link, obj.path)


@app_typer.command("list")
@_add_verbose_logger()
def list_virtualenvs(
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    verbose: VERBOSE_CLI = None,
) -> None:
    """List available central virtual environments"""
    venv_paths = list_venv_paths(workon_home)
    logger.debug("params: %s", locals())

    for p in sorted(venv_paths, key=lambda x: x.name):
        typer.echo(f"{p.name:25}  {p.resolve()}")


@app_typer.command("clean")
@_add_verbose_logger()
def clean_virtualenvs(
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
    yes: bool = False,
) -> None:
    """Remove missing broken virtual environment symlinks."""
    logger.debug("params: %s", locals())

    for path in get_invalid_symlinks(workon_home):
        if yes or typer.confirm(
            f"Remove {path} -> {path.readlink()}"
        ):  # pragma: no branch
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
@_add_verbose_logger()
def run_with_virtualenv(
    ctx: typer.Context,
    venv_name: VENV_NAME_CLI = None,
    venv_path: VENV_PATH_CLI = None,
    resolve: RESOLVE_CLI = False,
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    venv_patterns: VENV_PATTERNS_CLI = None,
    use_default_venv_patterns: USE_DEFAULT_VENV_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = None,
) -> None:
    """
    Run uv commands using using the named or specified virtual environment.

    For example, use ``uvw run -n my-env -- python ...`` is
    translated to ``uv run -p patt/to/my-env --no-project python ...``.

    If an option mirrors one of the command options (-n, etc), pass it after ``--``.

    Use ``--dry-run`` to echo the equivalent command to be run in the shell.
    """
    logger.info("params: %s", locals())

    if not ctx.args:
        typer.echo(ctx.get_help())
        return

    path = _select_virtualenv_path(
        venv_path=venv_path,
        venv_name=venv_name,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
        use_default_venv_patterns=use_default_venv_patterns,
        resolve=resolve,
    )

    command = uv_run(path, *ctx.args, dry_run=dry_run)
    if dry_run:  # pragma: no branch
        typer.echo(command)


# * Shell commands
@app_typer.command("shell-config")
def shell_config() -> None:
    """
    Use with ``eval "$(uv-workon shell-config)"``.


    This will add the subcommand ``uvw activate`` and ``uvw cd`` to the shell.  Without
    running shell config, ``activate`` and ``cd`` will just print the command to screen.
    """
    typer.echo(generate_shell_config())


@app_typer.command("activate")
def shell_activate(
    venv_name: VENV_NAME_CLI = None,
    venv_path: VENV_PATH_CLI = None,
    resolve: RESOLVE_CLI = False,
    no_command: NO_COMMAND_CLI = False,
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    venv_patterns: VENV_PATTERNS_CLI = None,
    use_default_venv_patterns: USE_DEFAULT_VENV_CLI = True,
) -> None:
    """Use to activate virtual environments."""
    path = _select_virtualenv_path(
        venv_path=venv_path,
        venv_name=venv_name,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
        use_default_venv_patterns=use_default_venv_patterns,
        resolve=resolve,
    )

    if (activate := path / "bin" / "activate").exists() or (
        activate := path / "Scripts" / "activate"
    ).exists():
        typer.echo(str(activate) if no_command else f"source {activate}")
    else:
        logger.error("No activate script found for path %s", path)
        raise typer.Exit(1)


@app_typer.command("cd")
def shell_cd(
    venv_name: VENV_NAME_CLI = None,
    venv_path: VENV_PATH_CLI = None,
    no_command: NO_COMMAND_CLI = False,
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    venv_patterns: VENV_PATTERNS_CLI = None,
    use_default_venv_patterns: USE_DEFAULT_VENV_CLI = True,
) -> None:
    """Command to change to parent directory of virtual environment."""
    path = _select_virtualenv_path(
        venv_path=venv_path,
        venv_name=venv_name,
        workon_home=workon_home,
        venv_patterns=venv_patterns,
        use_default_venv_patterns=use_default_venv_patterns,
        resolve=True,
    ).parent

    typer.echo(str(path) if no_command else f"cd {path}")


# * Working with ipykernels


@app_kernels.command("install")
@_add_verbose_logger()
def install_ipykernels(
    ctx: typer.Context,
    venv_names: Annotated[
        list[str] | None,
        typer.Option(
            "-n",
            "--name",
            help="Virtual environment names to install for.",
            autocompletion=_complete_virtualenv_names,
        ),
    ] = None,
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
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    venv_patterns: VENV_PATTERNS_CLI = None,
    use_default_venv_patterns: USE_DEFAULT_VENV_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = 0,  # noqa: ARG001
    yes: YES_CLI = False,
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
        use_default_venv_patterns=use_default_venv_patterns,
    ).items():
        if yes or (name not in kernelspecs) or typer.confirm(f"Reinstall {name}?"):
            display_name = display_format.format(name=name)
            command = uv_run(
                path.resolve() if resolve else path,
                "python",
                script,
                *(["--dry-run"] if dry_run else []),
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
@_add_verbose_logger()
def remove_kernels(
    names: Annotated[
        list[str] | None,
        typer.Option("-n", "--name", autocompletion=_complete_kernelspec_names),
    ] = None,
    venv_paths: VENV_PATHS_CLI = None,
    missing: Annotated[
        bool, typer.Option("--missing", help="Remove missing specs.")
    ] = False,
    workon_home: WORKON_HOME_CLI = WORKON_HOME_DEFAULT,
    venv_patterns: VENV_PATTERNS_CLI = None,
    use_default_venv_patterns: USE_DEFAULT_VENV_CLI = True,
    dry_run: DRY_RUN_CLI = False,
    verbose: VERBOSE_CLI = 0,  # noqa: ARG001
    yes: YES_CLI = False,
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
            use_default_venv_patterns=use_default_venv_patterns,
        )
    )
    if names is not None:
        to_remove.update(set(names))

    if missing:
        to_remove.update(set(get_broken_kernelspecs()))

    to_remove = to_remove.intersection(get_kernelspecs())

    to_remove_filtered = [
        name for name in to_remove if yes or typer.confirm(f"Remove {name}")
    ]

    if not to_remove_filtered:
        return

    logger.info("remove kernspecs %s", to_remove_filtered)

    if not dry_run:
        remove_kernelspecs(to_remove_filtered)


@app_kernels.command("list")
def list_kernels() -> None:
    """Interface to jupyter kernelspec list"""
    from .kernels import has_jupyter_client

    has_jupyter_client()

    from jupyter_client.kernelspecapp import ListKernelSpecs

    ListKernelSpecs().start()
