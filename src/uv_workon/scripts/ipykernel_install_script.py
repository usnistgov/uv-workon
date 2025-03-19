"""Script to be called under uv run to install an ipykernel"""

from __future__ import annotations

from argparse import ArgumentParser
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

    class _Parser:
        """Dummy class for parser."""

        args: list[str]
        dry_run: bool


def get_parser() -> ArgumentParser:
    """Basic parser."""
    parser = ArgumentParser(description="Interface to python -m ipykernel install")

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("args", type=str, nargs="+", default=[])

    return parser


def main(args: Sequence[str] | None = None) -> int:
    """Main program."""
    try:
        import ipykernel  # pyright: ignore[reportUnusedImport] # noqa: F401  # pylint: disable=unused-import
    except ImportError:
        import sys

        print(f"No ipykernel for {sys.executable}")  # noqa: T201
        return 0

    parser = get_parser()
    options = cast(
        "_Parser",
        parser.parse_args() if args is None else parser.parse_args(args),
    )
    args_ = ["python", "-m", "ipykernel", "install", *options.args]

    if options.dry_run:
        print("args", args_)  # noqa: T201
    else:
        import subprocess

        subprocess.run(args_, check=True)

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
