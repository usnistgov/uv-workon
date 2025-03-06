from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable


VirtualEnvPattern: TypeAlias = "str | Iterable[str] | None"
PathLike: TypeAlias = "str | os.PathLike[str]"
