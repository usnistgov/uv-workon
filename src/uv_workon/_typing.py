from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Iterable


VirtualEnvPattern: TypeAlias = "str | Iterable[str] | None"
