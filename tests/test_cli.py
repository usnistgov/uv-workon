# pyright: reportPrivateUsage=false
# pylint: disable=protected-access
from __future__ import annotations

import os
import shlex
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from uv_workon import cli
from uv_workon.core import generate_shell_config

if TYPE_CHECKING:
    from typing import Any

    from click import Command
    from click.testing import CliRunner
    from typer import Context


@pytest.mark.parametrize(
    ("args", "expected"),
    [  # pyright: ignore[reportUnknownArgumentType]
        (
            ([], True),
            nullcontext({".venv", "venv"}),
        ),
        (
            (["hello"], True),
            nullcontext({".venv", "venv", "hello"}),
        ),
        (
            (["hello"], False),
            nullcontext({"hello"}),
        ),
        (
            ([], False),
            pytest.raises(ValueError, match=r"No venv.*"),
        ),
    ],
)
def test__get_venv_dir_names(args: tuple[Any], expected: Any) -> None:
    with expected as e:
        out = cli._get_venv_dir_names(*args)
        assert set(out) == e


def test__get_input_paths(venvs_parent_path: Path) -> None:
    paths = list(venvs_parent_path.glob("has_dotvenv_*/.venv"))
    out = list(cli._get_input_paths(paths, parents=[]))

    expected = {
        venvs_parent_path / f"{x}_{i}" / y
        for x, y in (("has_dotvenv", ".venv"),)
        for i in range(3)
    }

    assert set(out) == expected

    # adding in a venv
    out = list(
        cli._get_input_paths(
            paths,
            parents=[venvs_parent_path / "has_venv_0"],
        )
    )

    expected2 = expected.copy()
    expected2.add(venvs_parent_path / "has_venv_0" / "venv")

    assert set(out) == expected2


def test_verbosity() -> None:
    import logging

    cli.list_virtualenvs(verbose=-1)
    assert cli.logger.level == logging.ERROR

    cli.list_virtualenvs(verbose=0)
    assert cli.logger.level == logging.WARNING

    cli.list_virtualenvs(verbose=1)
    assert cli.logger.level == logging.INFO

    cli.list_virtualenvs(verbose=2)
    assert cli.logger.level == logging.DEBUG


def test_version(
    click_app: Command,
    clirunner: CliRunner,
) -> None:
    from uv_workon import __version__

    out = clirunner.invoke(
        click_app,
        ["--version"],
    )

    assert f"uv-workon, version {__version__}" in out.output


@pytest.mark.parametrize(
    ("pattern", "parts"),
    [
        ("is_venv*", ("is_venv_{i}",)),
        ("has_dotvenv_*", ("has_dotvenv_{i}", ".venv")),
        ("has_dotvenv_*/.venv", ("has_dotvenv_{i}", ".venv")),
        ("has_venv_*", ("has_venv_{i}", "venv")),
        ("has_venv_*/venv", ("has_venv_{i}", "venv")),
        ("bad_dotvenv_*", None),
        ("bad_dotvenv_*/.venv", None),
    ],
)
@pytest.mark.parametrize("resolve", [True, False])
@pytest.mark.parametrize("dry", [True, False])
def test_link_paths(
    click_app: Command,
    clirunner: CliRunner,
    workon_home: Path,
    venvs_parent_path: Path,
    pattern: str,
    parts: tuple[str] | None,
    resolve: bool,
    dry: bool,
) -> None:
    paths = venvs_parent_path.glob(pattern)

    clirunner.invoke(
        click_app,
        [
            "link",
            "--workon-home",
            str(workon_home),
            "-vv",
            *map(str, paths),
            *(["--resolve"] if resolve else []),
            *(["--dry-run"] if dry else []),
        ],
    )

    if dry:
        assert set(workon_home.glob("*")) == set()
        return

    expected_symlinks: set[Path] = (
        set()
        if parts is None
        else {workon_home / parts[0].format(i=i) for i in range(3)}
    )

    assert expected_symlinks == set(workon_home.glob("*"))

    if parts is not None:
        # look at readlink
        expected_paths = {
            venvs_parent_path.joinpath(*[_.format(i=i) for _ in parts])
            for i in range(3)
        }

        if not resolve:
            expected_paths = {
                Path(os.path.relpath(p, workon_home)) for p in expected_paths
            }

        print(expected_paths)
        assert expected_paths == {p.readlink() for p in workon_home.glob("*")}


def test_link_parent(
    click_app: Command, clirunner: CliRunner, workon_home: Path, venvs_parent_path: Path
) -> None:
    clirunner.invoke(
        click_app,
        [
            "link",
            "--workon-home",
            str(workon_home),
            "-vv",
            "--parent",
            str(venvs_parent_path),
        ],
    )

    expected_symlinks = {
        workon_home / fmt.format(i=i)
        for fmt in ("has_dotvenv_{i}", "has_venv_{i}", "is_venv_{i}")
        for i in range(3)
    }

    assert expected_symlinks == set(workon_home.glob("*"))


def test_link_help(
    click_app: Command,
    clirunner: CliRunner,
) -> None:
    out = clirunner.invoke(click_app, ["link"])

    assert "Create symlink from paths" in out.output


@pytest.mark.parametrize(
    ("cli_val", "environment_val", "expected"),
    [
        ("~/hello", None, "~/hello"),
        (None, "~/there", "~/there"),
        (None, None, "~/.virtualenvs"),
        ("~/a", "~/b", "~/a"),
        ("a/b", None, "a/b"),
    ],
)
def test_workon_home(
    click_app: Command,
    clirunner: CliRunner,
    environment_val: str | None,
    cli_val: str | None,
    expected: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    env = {"WORKON_HOME": environment_val} if environment_val else {}
    opts = [] if cli_val is None else ["--workon-home", cli_val]
    clirunner.invoke(click_app, ["list", "-vv", *opts], env=env)

    assert f"'workon_home': {Path(expected).expanduser()!r}" in caplog.text


def test_list(
    click_app: Command,
    clirunner: CliRunner,
    workon_home_with_is_venv: Path,
) -> None:
    out = clirunner.invoke(
        click_app, ["list", "--workon-home", str(workon_home_with_is_venv)]
    )

    links = sorted(workon_home_with_is_venv.glob("*"), key=lambda x: x.name)
    expected = "\n".join([f"{p.name:25}  {p.resolve()}" for p in links])
    assert expected == out.output.strip()


def test_name_completions(
    workon_home_with_is_venv: Path,
) -> None:
    class Dummy:
        """Dummy class"""

        def __init__(self, workon_home: Path) -> None:
            self.params: dict[str, Any] = {"workon_home": workon_home}

    d = cast("Context", Dummy(workon_home=workon_home_with_is_venv))
    assert sorted(cli._complete_virtualenv_names(d, "")) == [
        f"is_venv_{i}" for i in range(3)
    ]
    assert sorted(cli._complete_virtualenv_names(d, "is_venv_")) == [
        f"is_venv_{i}" for i in range(3)
    ]
    assert sorted(cli._complete_virtualenv_names(d, "is_venv_0")) == [
        f"is_venv_{i}" for i in range(1)
    ]


@pytest.mark.parametrize("dry", [True, False])
def test_clean(
    click_app: Command,
    clirunner: CliRunner,
    workon_home_with_is_venv: Path,
    venvs_parent_path: Path,
    dry: bool,
) -> None:
    paths = venvs_parent_path.glob("is_venv_*")
    clirunner.invoke(
        click_app,
        [
            "link",
            "--workon-home",
            str(workon_home_with_is_venv),
            "-vv",
            *map(str, paths),
        ],
    )

    # additional bad venv
    path = venvs_parent_path / "no_venv_0"
    link = workon_home_with_is_venv / "no_venv_0"

    link.symlink_to(path)

    assert link.exists()
    assert link.readlink() == path

    clirunner.invoke(
        click_app,
        [
            "clean",
            "--workon-home",
            str(workon_home_with_is_venv),
            "--yes",
            *(["--dry-run"] if dry else []),
        ],
    )

    if dry:
        assert link.exists()
    else:
        assert not link.exists()


def test_run_help(
    click_app: Command,
    clirunner: CliRunner,
) -> None:
    out = clirunner.invoke(
        click_app,
        ["run"],
    )

    assert "Run uv commands using" in out.output


@pytest.mark.parametrize("dry", [True])
@pytest.mark.parametrize("named", [True, False])
@pytest.mark.parametrize("resolve", [True, False])
# @pytest.mark.parametrize("resolve", [False])
def test_run(
    click_app: Command,
    clirunner: CliRunner,
    workon_home_with_is_venv: Path,
    dry: bool,
    named: bool,
    resolve: bool,
) -> None:
    args = ["python", "-c", "import sys; print(sys.executable)"]

    path = workon_home_with_is_venv / "is_venv_0"
    if resolve:
        path = path.resolve()

    opts = (
        ["-n", "is_venv_0"]
        if named
        else ["-p", str(workon_home_with_is_venv / "is_venv_0")]
    )

    out = clirunner.invoke(
        click_app,
        [
            "run",
            "--workon-home",
            str(workon_home_with_is_venv),
            *opts,
            *args,
            *(["--dry-run"] if dry else []),
            *(["--resolve"] if resolve else []),
        ],
    )

    if dry:
        expected = f"VIRTUAL_ENV={path} UV_PROJECT_ENVIRONMENT={path} uv run -p {path} --no-project {shlex.join(args)}"
        assert expected == out.output.strip()


def test_install_ipykernels(
    click_app: Command,
    clirunner: CliRunner,
    workon_home_with_is_venv: Path,
) -> None:
    pass


def test_shell_config(click_app: Command, clirunner: CliRunner) -> None:
    out = clirunner.invoke(click_app, ["shell-config"])
    assert out.output.strip() == generate_shell_config().strip()


def test_shell_activate(
    click_app: Command,
    clirunner: CliRunner,
    workon_home_with_is_venv: Path,
) -> None:
    out = clirunner.invoke(
        click_app,
        ["activate", "-n", "is_venv_0", "--workon-home", str(workon_home_with_is_venv)],
    )
    assert f"source {workon_home_with_is_venv}/is_venv_0" in out.output

    out = clirunner.invoke(
        click_app,
        [
            "activate",
            "-p",
            str(workon_home_with_is_venv / "is_venv_1"),
            "--workon-home",
            str(workon_home_with_is_venv),
        ],
    )
    assert f"source {workon_home_with_is_venv}/is_venv_1" in out.output

    out = clirunner.invoke(
        click_app,
        [
            "activate",
            "-p",
            str(workon_home_with_is_venv / "is_venv_2"),
            "--workon-home",
            str(workon_home_with_is_venv),
        ],
    )

    assert out.exit_code == 1


def test_shell_cd(
    click_app: Command,
    clirunner: CliRunner,
    workon_home_with_is_venv: Path,
) -> None:
    out = clirunner.invoke(
        click_app,
        ["cd", "-n", "is_venv_0", "--workon-home", str(workon_home_with_is_venv)],
    )

    path = (workon_home_with_is_venv / "is_venv_0").resolve().parent

    assert f"cd {path}" in out.output


def test__main__() -> None:
    from subprocess import check_call

    assert not check_call(["python", "-m", "uv_workon"])
