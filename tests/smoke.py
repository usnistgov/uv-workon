"""Smoke test for package"""

import sys

from uv_workon import __version__


def _main() -> None:
    assert isinstance(__version__, str)


if __name__ == "__main__":
    sys.exit(_main())
