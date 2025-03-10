from __future__ import annotations

from contextlib import nullcontext
from functools import partial
from typing import TYPE_CHECKING

import pytest

from uv_workon.core import (
    NoVirtualEnvError,
    VirtualEnvPathAndLink,
    generate_shell_config,
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
        (("has_dotvenv_0",), nullcontext(("has_dotvenv_0", ".venv"))),
        (("has_venv_0", "venv"), nullcontext(("has_venv_0", "venv"))),
        (("is_venv_0",), nullcontext(("is_venv_0",))),
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
