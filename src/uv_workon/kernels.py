"""
Working with ipykernel (:mod:`~uv_workon.kernels`)
==================================================
"""

from __future__ import annotations

import logging
from collections.abc import Iterator  # noqa: TC003
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


logger = logging.getLogger(__name__)


def has_jupyter_client() -> None:
    """Raise error if does not have jupyter-client"""
    if find_spec("jupyter_client") is None:
        msg = "jupyter_client not installed.  Install it directly or by using `jupyter-client` extra"
        raise ModuleNotFoundError(msg)


def get_ipykernel_install_script_path() -> str:
    """Get the path to ipykernel install script"""
    from importlib.resources import files

    return str(
        files("uv_workon").joinpath("scripts").joinpath("ipykernel_install_script.py")
    )


@lru_cache
def get_kernelspecs() -> dict[str, Any]:
    """Get all kernelspecs"""
    has_jupyter_client()
    from jupyter_client.kernelspecapp import ListKernelSpecs

    return ListKernelSpecs().kernel_spec_manager.get_all_specs()


def get_broken_kernelspecs() -> dict[str, Any]:
    """Get list of broken kernels"""
    from shutil import which

    broken: dict[str, Any] = {}
    for name, data in get_kernelspecs().items():
        exe = data["spec"]["argv"][0]
        if Path(exe).exists() or which(exe):
            continue
        broken[name] = data
    return broken


def remove_kernelspecs(names: list[str]) -> None:
    """Remove named kernels."""
    has_jupyter_client()
    from jupyter_client.kernelspecapp import RemoveKernelSpec

    RemoveKernelSpec(spec_names=names, force=True).start()


def complete_kernelspec_names(incomplete: str) -> Iterator[str]:
    """Complete possible kernel specs"""
    valid_names = get_kernelspecs()
    yield from (name for name in valid_names if name.startswith(incomplete))
