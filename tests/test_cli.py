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

if TYPE_CHECKING:
    import argparse
    from typing import Any


def parse_args(arg: str = "") -> argparse.Namespace:
    parser, _ = cli.get_parser()
    return parser.parse_args(shlex.split(arg))


def parse_args_as_dict(arg: str = "") -> dict[str, Any]:
    return vars(parse_args(arg))


def base_cli_options(
    command: str = "link",
    venv: list[str] | None = None,
    no_default_venv: bool = False,
    paths: list[Path] | None = None,
    parent: list[Path] | None = None,
    workon_home: Path | None = None,
    force: bool = False,
    resolve: bool = False,
    verbose: int = 0,
    dry_run: bool = False,
) -> dict[str, Any]:
    return {
        "command": command,
        "venv": [] if venv is None else venv,
        "no_default_venv": no_default_venv,
        "paths": [] if paths is None else paths,
        "parent": [] if parent is None else parent,
        "workon_home": workon_home,
        "force": force,
        "resolve": resolve,
        "verbose": verbose,
        "dry_run": dry_run,
    }


@pytest.mark.parametrize(
    ("arg", "kwargs"),
    [
        (
            "",
            {},
        ),
        ("a/b c/d", {"paths": [Path("a/b"), Path("c/d")]}),
        ("--parent a/b --parent c/d", {"parent": [Path("a/b"), Path("c/d")]}),
        (
            "--dry-run",
            {"dry_run": True},
        ),
        ("--venv hello", {"venv": ["hello"]}),
        ("-o a/dir", {"workon_home": Path("a/dir")}),
    ],
)
def test_parser_link(arg: str, kwargs: dict[str, Any]) -> None:
    assert parse_args_as_dict(f"link {arg}") == base_cli_options(**kwargs)


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


def test__main() -> None:
    from subprocess import check_output

    out = check_output(["python", "-m", "uv_workon"]).decode()
    assert "Program to work" in out


def test_verbosity() -> None:
    import logging

    cli.main([])
    assert not cli.logger.level

    cli.set_verbosity_level(-1)
    assert cli.logger.level == logging.ERROR  # type: ignore[comparison-overlap]

    cli.set_verbosity_level(0)
    assert cli.logger.level == logging.WARNING

    cli.set_verbosity_level(1)
    assert cli.logger.level == logging.INFO

    cli.set_verbosity_level(2)
    assert cli.logger.level == logging.DEBUG
