# pyright: reportPrivateUsage=false
# pylint: disable=protected-access
from __future__ import annotations

import os
import shlex
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from uv_workon import cli
from uv_workon.core import generate_shell_config

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from click.testing import CliRunner


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
def test__get_workon_home(
    monkeypatch: Any, cli_val: str | None, environment_val: str | None, expected: Path
) -> None:
    if environment_val is not None:
        monkeypatch.setenv("WORKON_HOME", environment_val)
    elif "WORKON_HOME" in os.environ:
        monkeypatch.delenv("WORKON_HOME")

    assert (
        cli._get_workon_home(None if cli_val is None else Path(cli_val)).expanduser()
        == Path(expected).expanduser()
    )


def test_verbosity() -> None:
    import logging

    cli.list_venvs(verbose=-1)
    assert cli.logger.level == logging.ERROR

    cli.list_venvs(verbose=0)
    assert cli.logger.level == logging.WARNING

    cli.list_venvs(verbose=1)
    assert cli.logger.level == logging.INFO

    cli.list_venvs(verbose=2)
    assert cli.logger.level == logging.DEBUG


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
def test_symlink_venvs_paths(
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
        cli.app,
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


def test_symlink_venvs_parent(
    clirunner: CliRunner, workon_home: Path, venvs_parent_path: Path
) -> None:
    clirunner.invoke(
        cli.app,
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


@pytest.mark.parametrize(
    "options",
    [
        ("--resolve",),
        ("--full-path",),
        (),
    ],
)
def test_list(
    clirunner: CliRunner, workon_home_with_is_venv: Path, options: tuple[str]
) -> None:
    out = clirunner.invoke(
        cli.app, ["list", "--workon-home", str(workon_home_with_is_venv), *options]
    )

    links = workon_home_with_is_venv.glob("*")

    expected: Iterable[Any]
    if options == ("--resolve",):
        expected = (x.resolve() for x in links)

    elif options == ("--full-path",):
        expected = links

    else:
        expected = (x.name for x in links)

    assert "\n".join(map(str, sorted(expected))) == out.output.strip()


@pytest.mark.parametrize("dry", [True, False])
def test_clean(
    clirunner: CliRunner,
    workon_home_with_is_venv: Path,
    venvs_parent_path: Path,
    dry: bool,
) -> None:
    paths = venvs_parent_path.glob("is_venv_*")
    clirunner.invoke(
        cli.app,
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
        cli.app,
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


@pytest.mark.parametrize("dry", [True])
@pytest.mark.parametrize("named", [True, False])
@pytest.mark.parametrize("resolve", [True, False])
# @pytest.mark.parametrize("resolve", [False])
def test_run(
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
        cli.app,
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


def test_shell_config(clirunner: CliRunner) -> None:
    out = clirunner.invoke(cli.app, ["shell-config"])
    assert out.output.strip() == generate_shell_config().strip()
