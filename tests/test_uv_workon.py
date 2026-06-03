"""Tests for `uv-workon` package."""

from __future__ import annotations

import re

<<<<<<< before updating
=======
import pytest
from typer.testing import CliRunner

from uv_workon import cli, example_function

>>>>>>> after updating

def test_version() -> None:
    from uv_workon import __version__

    assert isinstance(__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+.*$", __version__) is not None
<<<<<<< before updating
=======


@pytest.fixture
def response() -> tuple[int, int]:
    return 1, 2


def test_example_function(response: tuple[int, int]) -> None:
    expected = 3
    assert example_function(*response) == expected


def test_command_line_interface() -> None:
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert not result.exit_code
    assert "uv_workon.cli.main" in result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert not help_result.exit_code
    assert "--help" in help_result.output
    assert "Show this message and exit." in help_result.output
>>>>>>> after updating
