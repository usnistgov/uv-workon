from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


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
