from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .caret import Caret


@dataclass(slots=True)
class IodxField:
    """A key-value item written as ``key = value``."""

    key: Any
    value: Any
    caret: Caret | None = field(default=None, compare=False)


@dataclass(slots=True)
class IodxComment:
    """A first-class single-line or block comment."""

    text: str
    single_line: bool = True
    caret: Caret | None = field(default=None, compare=False)


@dataclass(slots=True)
class IodxEntity:
    """A named or unnamed IODX entity with positional and key-value children."""

    name: str | None
    children: list[Any] = field(default_factory=list)
    caret: Caret | None = field(default=None, compare=False)
    children_carets: list[Caret | None] = field(default_factory=list, compare=False)

    def has_field(self, key: Any) -> bool:
        return any(isinstance(child, IodxField) and child.key == key for child in self.children)

    def get_field(self, key: Any, default: Any = None) -> Any:
        for child in self.children:
            if isinstance(child, IodxField) and child.key == key:
                return child.value
        return default

    @property
    def fields(self) -> list[IodxField]:
        return [child for child in self.children if isinstance(child, IodxField)]

    def with_replaced(self, key: Any, value: Any) -> IodxEntity:
        if key is None:
            raise ValueError("key is None")
        children = [
            IodxField(key, value, child.caret)
            if isinstance(child, IodxField) and child.key == key
            else child
            for child in self.children
        ]
        return IodxEntity(self.name, children, self.caret, self.children_carets.copy())
