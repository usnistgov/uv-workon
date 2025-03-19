from __future__ import annotations

from importlib.util import find_spec
from typing import TYPE_CHECKING

import pytest

from uv_workon import kernels

if TYPE_CHECKING:
    from typing import Any

    from pytest_mock import MockerFixture

_has_jupyter_client = find_spec("jupyter_client") is not None

skip_if_no_jupyter_client = pytest.mark.skipif(
    not _has_jupyter_client, reason="Must install jupyter client for this test."
)


def test_get_ipykernel_install_script_path() -> None:
    from importlib.resources import files

    assert (
        str(
            files("uv_workon")
            .joinpath("scripts")
            .joinpath("ipykernel_install_script.py")
        )
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
def test_get_kernelspec_0() -> None:
    assert isinstance(kernels.get_kernelspecs(), dict)
    assert isinstance(kernels.get_broken_kernelspecs(), dict)
    kernels.remove_kernelspecs([])


@skip_if_no_jupyter_client
def test_get_broken_kernelspecs(
    mocker: MockerFixture,
    dummy_kernelspec: dict[str, Any],
    mocked_get_kernelspec: Any,
) -> None:
    assert kernels.get_broken_kernelspecs() == {
        k: v for k, v in dummy_kernelspec.items() if k != "good"
    }
    assert mocked_get_kernelspec.mock_calls == [mocker.call()]


@skip_if_no_jupyter_client
def test_complete_kernelspec_names(
    mocker: MockerFixture,
    mocked_get_kernelspec: Any,
) -> None:
    names = ["dummy0", "dummy1", "good"]

    assert list(kernels.complete_kernelspec_names("")) == names
    assert list(kernels.complete_kernelspec_names("d")) == names[:-1]
    assert list(kernels.complete_kernelspec_names("g")) == names[-1:]

    assert mocked_get_kernelspec.mock_calls == [mocker.call()] * 3


@skip_if_no_jupyter_client
def test_remove_kernelspecs(mocker: MockerFixture) -> None:
    mock_removekernelspec = mocker.patch(
        "jupyter_client.kernelspecapp.RemoveKernelSpec", autospec=True
    )
    kernels.remove_kernelspecs(["a", "b"])
    assert mock_removekernelspec.mock_calls == [
        mocker.call(spec_names=["a", "b"], force=True),
        mocker.call().start(),
    ]
