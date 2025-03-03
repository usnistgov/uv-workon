from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from uv_workon.core import find_venvs, get_workon_script_path, is_valid_venv

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("pattern", "args", "valid"),
    [
        ("has_dotvenv_{}", (".venv",), True),
        ("has_venv_{}", ("venv",), True),
        ("is_venv_{}", (), True),
        ("bad_dotvenv_{}", (".venv",), False),
        ("bad_venv_{}", ("venv",), False),
        ("no_venv_{}", (), False),
    ],
)
def test_is_valid_venv(
    venvs_parent_path: Path, pattern: str, args: tuple[str], valid: bool
) -> None:
    for i in range(3):
        path = venvs_parent_path.joinpath(pattern.format(i), *args)
        print(path)

        assert is_valid_venv(path) == valid


def test_find_venvs_explicit(venvs_parent_path: Path) -> None:
    # pylint: disable=use-implicit-booleaness-not-comparison
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


def test_get_workon_script_path() -> None:
    from importlib.resources import files

    assert (
        str(files("uv_workon").joinpath("scripts", "workon.sh"))
        == get_workon_script_path()
    )
