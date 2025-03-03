from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_foo(example_path: Path, venvs_parent_path: Path) -> None:
    print(example_path.absolute())
    print(venvs_parent_path.absolute())


def test_bar(example_path: Path, venvs_parent_path: Path) -> None:
    print(example_path.absolute())
    print(venvs_parent_path.absolute())
