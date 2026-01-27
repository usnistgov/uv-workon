"""
Top level API (:mod:`uv_workon`)
======================================================
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:  # noqa: RUF067
    __version__ = _version("uv-workon")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "999"


__author__ = """William P. Krekelberg"""
__email__ = "wpk@nist.gov"  # noqa: RUF067


__all__ = [
    "__version__",
]
