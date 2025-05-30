"""
Utilities (:mod:`~uv_workon.utils`)
===================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence


def select_option(
    options: Sequence[str],
    title: str = "",
    usage: bool = True,
) -> str:
    """Use selector"""
    from simple_term_menu import (  # pyright: ignore[reportMissingTypeStubs]
        TerminalMenu,
    )

    title = " ".join(
        [
            *([title] if title else []),
            *(
                ["use arrows or j/k to move down/up, or / to limit by name"]
                if usage
                else []
            ),
        ]
    )
    index = cast("int", TerminalMenu(options, title=title or None).show())
    return options[index]
