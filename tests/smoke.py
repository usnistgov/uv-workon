"""Smoke test for package"""

import sys

from uv_workon import __version__


def _main() -> int:
    assert isinstance(__version__, str)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
