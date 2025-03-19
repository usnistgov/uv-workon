from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import pytest

from uv_workon.core import (
    VirtualEnvPathAndLink,
    generate_shell_config,
    uv_run,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def find_venvs_interface(
    *args: Path, workon_home: Path, venv_patterns: list[str] | None = None
) -> list[Path]:
    if venv_patterns is None:
        venv_patterns = [".venv", "venv"]

    return [
        obj.path
        for obj in VirtualEnvPathAndLink.from_paths_and_workon(
            args, workon_home=workon_home, venv_patterns=venv_patterns
        )
    ]


def test_find_venvs_explicit(venvs_parent_path: Path, workon_home: Path) -> None:
    find_venvs = partial(find_venvs_interface, workon_home=workon_home)
    paths_dotvenv = list(venvs_parent_path.glob("has_dotvenv_*/.venv"))

    assert find_venvs(*paths_dotvenv) == paths_dotvenv
    assert find_venvs(*venvs_parent_path.glob("has_dotvenv_*")) == paths_dotvenv
    assert find_venvs(*venvs_parent_path.glob("has_dotvenv_*"), venv_patterns=[]) == []

    paths_venv = list(venvs_parent_path.glob("has_venv_*/venv"))
    assert find_venvs(*paths_venv) == paths_venv

    paths_is_venv = list(venvs_parent_path.glob("is_venv_*"))
    assert find_venvs(*paths_is_venv) == paths_is_venv

    assert find_venvs(*venvs_parent_path.glob("bad_dotvenv_*/.venv")) == []
    assert find_venvs(*venvs_parent_path.glob("bad_dotvenv_*")) == []

    assert find_venvs(*venvs_parent_path.glob("bad_venv_*/venv")) == []
    assert find_venvs(*venvs_parent_path.glob("bad_venv_*")) == []

    assert find_venvs(*venvs_parent_path.glob("no_venv_*")) == []


def test_find_venvs_with_name(venvs_parent_path: Path, workon_home: Path) -> None:
    paths = sorted(venvs_parent_path.glob("has_dotvenv_*"), key=lambda x: x.name)

    out = list(
        VirtualEnvPathAndLink.from_paths_and_workon(
            paths, workon_home=workon_home, venv_patterns=[".venv", "venv"]
        )
    )

    assert [x.link.name for x in out] == [f"has_dotvenv_{i}" for i in range(3)]

    out = list(
        VirtualEnvPathAndLink.from_paths_and_workon(
            paths,
            names=["a", "b", "c"],
            workon_home=workon_home,
            venv_patterns=[".venv", "venv"],
        )
    )

    assert [x.link.name for x in out] == ["a", "b", "c"]

    out = list(
        VirtualEnvPathAndLink.from_paths_and_workon(
            paths[:1],
            names="a",
            workon_home=workon_home,
            venv_patterns=[".venv", "venv"],
        )
    )

    assert [x.link.name for x in out] == ["a"]

    with pytest.raises(ValueError, match=r".* shorter.*"):
        out = list(
            VirtualEnvPathAndLink.from_paths_and_workon(
                paths,
                names="a",
                workon_home=workon_home,
                venv_patterns=[".venv", "venv"],
            )
        )


def test_generate_shell_config() -> None:
    assert "_UV_WORKON" in generate_shell_config()


def test_uv_run_error() -> None:
    from tempfile import TemporaryDirectory

    args = ["python", "-c", "import sys; print(sys.executable)"]
    with TemporaryDirectory() as e, pytest.raises(CalledProcessError):
        _ = uv_run(Path(e), *args, dry_run=False)

    import sys

    _ = uv_run(Path(sys.executable), *args, dry_run=False)


def test_uv_run(mocker: MockerFixture) -> None:
    mock_subprocess_run = mocker.patch("subprocess.run", autospec=True)

    venv_path = Path.cwd().resolve()
    args = ["python", "-c", "import sys"]

    uv_run(venv_path, *args)

    # pylint: disable=duplicate-code
    assert mock_subprocess_run.mock_calls == [
        mocker.call(
            (
                "uv",
                "run",
                "-p",
                str(venv_path),
                "--no-project",
                *args,
            ),
            check=True,
            env={
                **os.environ,
                "VIRTUAL_ENV": str(venv_path),
                "UV_PROJECT_ENVIRONMENT": str(venv_path),
            },
        )
    ]
