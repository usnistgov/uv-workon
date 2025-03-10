"""Tests for `uv-workon` package."""

from __future__ import annotations


def test_version() -> None:
    from uv_workon import __version__

    assert __version__ != "999"
