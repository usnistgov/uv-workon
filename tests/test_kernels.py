from __future__ import annotations

import sys
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import call, patch

import pytest

from uv_workon import kernels

if TYPE_CHECKING:
    from typing import Any

_has_jupyter_client = find_spec("jupyter_client") is not None

skip_if_no_jupyter_client = pytest.mark.skipif(
    not _has_jupyter_client, reason="Must install jupyter client for this test."
)


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
def mock_get_kernelspecs(dummy_kernelspec: dict[str, Any]) -> Any:
    with patch(
        "uv_workon.kernels.get_kernelspecs", return_value=dummy_kernelspec
    ) as mocked:
        yield mocked


@pytest.fixture
def mock_removekernelspec() -> Any:
    with patch(
        "jupyter_client.kernelspecapp.RemoveKernelSpec", autospec=True
    ) as mocked:
        yield mocked


def test_get_ipykernel_install_script_path() -> None:
    from importlib.resources import files

    assert (
        str(files("uv_workon").joinpath("scripts", "ipykernel_install_script.py"))
        == kernels.get_ipykernel_install_script_path()
    )


# dumb tests.  to be replaced with better someday...
def test_has_jupyter_client() -> None:
    if _has_jupyter_client:
        kernels.has_jupyter_client()
    else:
        with pytest.raises(ModuleNotFoundError):
            kernels.has_jupyter_client()


@skip_if_no_jupyter_client
def test_get_kernelspec() -> None:
    assert isinstance(kernels.get_kernelspecs(), dict)
    assert isinstance(kernels.get_broken_kernelspecs(), dict)
    kernels.remove_kernelspecs([])


@skip_if_no_jupyter_client
def test_get_broken_kernelspecs(
    mock_get_kernelspecs: Any, dummy_kernelspec: dict[str, Any]
) -> None:
    assert kernels.get_broken_kernelspecs() == {
        k: v for k, v in dummy_kernelspec.items() if k != "good"
    }
    assert mock_get_kernelspecs.mock_calls == [call()]


@skip_if_no_jupyter_client
def test_remove_kernelspecs(mock_removekernelspec: Any) -> None:
    kernels.remove_kernelspecs(["a", "b"])
    assert mock_removekernelspec.mock_calls == [
        call(spec_names=["a", "b"], force=True),
        call().start(),
    ]
