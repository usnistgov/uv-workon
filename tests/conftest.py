from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Generator

    from click import Command


@pytest.fixture(scope="session")
def click_app() -> Command:
    import uv_workon._click

    return uv_workon._click.click_app  # pylint: disable=protected-access


@pytest.fixture
def example_path(tmp_path: Path) -> Generator[Path]:
    # change to example_path
    old_cwd = Path.cwd()
    os.chdir(tmp_path)

    assert Path.cwd().absolute() == tmp_path.absolute()

    yield tmp_path.absolute()
    # Cleanup?
    os.chdir(old_cwd)

    assert Path.cwd().absolute() == old_cwd.absolute()


@pytest.fixture
def workon_home(example_path: Path) -> Generator[Path]:
    out = example_path / "venvs"
    out.mkdir(exist_ok=True)

    yield out

    shutil.rmtree(out)


@pytest.fixture(scope="session")
def venvs_parent_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("examples")

    parent_path = out / "a" / "b" / "c"
    parent_path.mkdir(parents=True)

    for i in range(3):
        for args in (
            (f"has_dotvenv_{i}", ".venv"),
            (f"has_venv_{i}", "venv"),
            (f"is_venv_{i}",),
        ):
            d = parent_path.joinpath(*args)
            d.mkdir(parents=True)
            (d / "pyvenv.cfg").write_text("hello")

        for args in (
            (f"bad_dotvenv_{i}", ".venv"),
            (f"bad_venv_{i}", "venv"),
            (f"no_venv_{i}",),
        ):
            d = parent_path.joinpath(*args)
            d.mkdir(parents=True)

    return parent_path


@pytest.fixture(scope="session")
def clirunner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def workon_home_with_is_venv(
    click_app: Command, workon_home: Path, venvs_parent_path: Path, clirunner: CliRunner
) -> Path:
    paths = venvs_parent_path.glob("is_venv_*")
    clirunner.invoke(
        click_app, ["link", "--workon-home", str(workon_home), "-vv", *map(str, paths)]
    )

    return workon_home
