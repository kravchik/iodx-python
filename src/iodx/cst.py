from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .caret import Caret


@dataclass(slots=True)
class IodxCst:
    """Concrete syntax tree node produced by the IODX parser."""

    type: str
    caret: Caret | None
    value: Any = None
    children: list[IodxCst] = field(default_factory=list)
    child_by_field: dict[str, IodxCst] = field(default_factory=dict)

    def __str__(self) -> str:
        if not self.children:
            return self.type
        return f"{self.type}([{', '.join(map(str, self.children))}])"

    __repr__ = __str__
