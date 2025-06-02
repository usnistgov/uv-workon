from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from uv_workon.validate import (
    NoVirtualEnvError,
    infer_virtualenv_path_raise,
    is_valid_virtualenv,
    validate_dir_exists,
    validate_is_virtualenv,
    validate_symlink,
    validate_venv_patterns,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from uv_workon._typing import VirtualEnvPattern


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

        assert is_valid_virtualenv(path) == valid

        if valid:
            assert validate_is_virtualenv(path) == path
        else:
            with pytest.raises(
                NoVirtualEnvError, match=r".* is not a valid virtual .*"
            ):
                _ = validate_is_virtualenv(path)


def test_validate_dir_exists(venvs_parent_path: Path) -> None:
    assert validate_dir_exists(venvs_parent_path) == venvs_parent_path

    with pytest.raises(ValueError, match=r".* is not a directory."):
        _ = validate_dir_exists(venvs_parent_path / "a-dummy-dir")


def test_validate_symlink(venvs_parent_path: Path) -> None:
    with pytest.raises(ValueError, match=r".* exists and is not a symlink"):
        _ = validate_symlink(venvs_parent_path)

    p = venvs_parent_path / "tmp"
    p.mkdir()

    link = p / "link"
    link.symlink_to(venvs_parent_path)

    assert validate_symlink(link) == link


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (
            ("has_dotvenv_0",),
            nullcontext(  # pyre-ignore[no-matching-overload,bad-argument-type]
                ("has_dotvenv_0", ".venv")
            ),
        ),
        (
            ("has_venv_0", "venv"),
            nullcontext(  # pyre-ignore[no-matching-overload,bad-argument-type]
                ("has_venv_0", "venv")
            ),
        ),
        (
            ("is_venv_0",),
            nullcontext(  # pyre-ignore[no-matching-overload,bad-argument-type]
                ("is_venv_0",)
            ),
        ),
        (
            ("bad_dotvenv_0",),
            pytest.raises(NoVirtualEnvError, match=r"No venv found .*"),
        ),
        (
            ("bad_dotvenv_0", ".venv"),
            pytest.raises(NoVirtualEnvError, match=r"No venv found .*"),
        ),
        (("no_venv",), pytest.raises(NoVirtualEnvError, match=r"No venv found .*")),
    ],
)
def test_infer_virtualenv_path_raise(
    venvs_parent_path: Path, args: tuple[str], expected: Any
) -> None:
    with expected as e:
        path = venvs_parent_path.joinpath(*args)
        out = infer_virtualenv_path_raise(path, venv_patterns=[".venv", "venv"])

        assert out == venvs_parent_path.joinpath(*e)


@pytest.mark.parametrize(
    ("venv_patterns", "expected"),
    [
        ("hello", ["hello"]),
        (iter(["hello"]), ["hello"]),
        (("hello",), ["hello"]),
        (["hello"], ["hello"]),
        (None, []),
    ],
)
def test_validate_venv_patterns(
    venv_patterns: VirtualEnvPattern, expected: list[str]
) -> None:
    assert validate_venv_patterns(venv_patterns) == expected
