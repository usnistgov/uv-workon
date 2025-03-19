from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any

    from click import Command
    from pytest_mock import MockerFixture


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

    # dummy make activate files ...
    d = parent_path / "is_venv_0" / "bin"
    d.mkdir()
    (d / "activate").touch()

    d = parent_path / "is_venv_1" / "Scripts"
    d.mkdir()
    (d / "activate").touch()

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


@pytest.fixture
def dummy_kernelspec() -> dict[str, Any]:
    p = Path.cwd().resolve()
    out = {
        name: {
            "resource_dir": str(p / name),
            "spec": {
                "argv": [
                    str(p / name / "bin" / "python"),
                    "-Xfrozen_modules=off",
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "env": {},
                "display_name": "Python [venv: dummy0]",
                "language": "python",
                "interrupt_mode": "signal",
                "metadata": {"debugger": True},
            },
        }
        for name in ("dummy0", "dummy1")
    }

    out["good"] = {
        "resource_dir": str(p / "good"),
        "spec": {
            "argv": [
                sys.executable,
                "-Xfrozen_modules=off",
                "-m",
                "ipykernel_launcher",
                "-f",
                "{connection_file}",
            ],
            "env": {},
            "display_name": "Python [venv: dummy0]",
            "language": "python",
            "interrupt_mode": "signal",
            "metadata": {"debugger": True},
        },
    }
    return out


@pytest.fixture
def dummy_kernelspec_with_replace(dummy_kernelspec: dict[str, Any]) -> dict[str, Any]:
    p = Path.cwd().resolve()
    name = "is_venv_0"
    return {
        name: {
            "resource_dir": str(p / name),
            "spec": {
                "argv": [
                    str(p / name / "bin" / "python"),
                    "-Xfrozen_modules=off",
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "env": {},
                "display_name": "Python [venv: dummy0]",
                "language": "python",
                "interrupt_mode": "signal",
                "metadata": {"debugger": True},
            },
        },
        **dummy_kernelspec,
    }


@pytest.fixture
def mocked_get_kernelspec(
    mocker: MockerFixture, dummy_kernelspec: dict[str, Any]
) -> Any:
    return mocker.patch(
        "uv_workon.kernels.get_kernelspecs",
        autospec=True,
        return_value=dummy_kernelspec,
    )
