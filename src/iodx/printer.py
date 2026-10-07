from __future__ import annotations

import math
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TextIO

from .cst import IodxCst
from .entity import IodxComment, IodxEntity, IodxField
from .errors import IodxParseError
from .escaping import escape_double_quotes, escape_single_quotes
from .numbers import IodxFloat32, IodxFloat64, IodxInt64
from .parser import parse


class IodxPrinter:
    """Print and format CST or syntax-model values as IODX."""

    def __init__(
        self,
        *,
        max_width: int = 100,
        max_local_width: int = sys.maxsize,
        compact_from_level: int = 0,
        tab: str = "  ",
    ) -> None:
        self.max_width = max_width
        self.max_local_width = max_local_width
        self.compact_from_level = compact_from_level
        self.tab = tab
        self._level = 0

    def render(self, value: Any) -> str:
        """Render one syntax value or CST node."""

        return "\n".join(self._print_value(0, value))

    def render_all(self, values: Sequence[Any]) -> str:
        """Render values without an enclosing entity."""

        return "\n".join(self._print_list(values, 0, None, None, add_tabs=False))

    def without_quotes(self, value: str) -> bool:
        """Return whether a string is exactly one safe unquoted token."""

        if not value or value in {"true", "false", "null", "="}:
            return False
        try:
            document = parse(value)
        except IodxParseError:
            return False
        if len(document.children) != 1:
            return False
        node = document.children[0]
        return node.type in {"ANY_LITERAL", "ANY_OPERATOR", "ANY_SEPARATOR"}

    def value_to_string(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            if self.without_quotes(value):
                return value
            if "'" in value:
                return f'"{escape_double_quotes(value)}"'
            return f"'{escape_single_quotes(value)}'"
        if isinstance(value, IodxInt64):
            return f"{int(value)}l"
        if isinstance(value, IodxFloat32):
            return f"{_float_text(value, compact_integer=True)}f"
        if isinstance(value, IodxFloat64):
            return f"{_float_text(value, compact_integer=True)}d"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return f"{_float_text(value, compact_integer=True)}d"
        raise TypeError(f"Unsupported IODX value type: {type(value).__name__}")

    def _print_value(self, start_at: int, value: Any) -> list[str]:
        if isinstance(value, IodxCst):
            return self._print_cst(start_at, value)
        if isinstance(value, IodxField):
            result = self._print_value(start_at, value.key)
            value_result = self._print_value(start_at + len(self.tab), value.value)
            result[-1] = f"{result[-1]} = {value_result[0]}"
            result.extend(value_result[1:])
            return result
        if isinstance(value, IodxComment):
            delimiters = ("//", "") if value.single_line else ("/*", "*/")
            return [f"{delimiters[0]}{value.text}{delimiters[1]}"]
        if isinstance(value, IodxEntity):
            left = "(" if value.name is None else f"{value.name}("
            return self._print_list(value.children, start_at, left, ")", add_tabs=True)
        if isinstance(value, Mapping):
            if not value:
                return ["(=)"]
            fields = [IodxField(key, item) for key, item in value.items()]
            return self._print_list(fields, start_at, "(", ")", add_tabs=True)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return self._print_list(value, start_at, "(", ")", add_tabs=True)
        return [self.value_to_string(value)]

    def _print_cst(self, start_at: int, node: IodxCst) -> list[str]:
        if node.type == "LIST_BODY":
            return self._print_list(node.children, start_at, None, None, add_tabs=False)
        if node.type in {"NAMED_CLASS", "UNNAMED_CLASS"}:
            name = ""
            if node.type == "NAMED_CLASS":
                name = _literal_text(node.child_by_field["name"].value)
            return self._print_list(
                node.child_by_field["body"].children,
                start_at,
                f"{name}(",
                ")",
                add_tabs=True,
            )
        if node.type == "COMMENT_SINGLE_LINE":
            return [f"//{node.value}"]
        if node.type == "COMMENT_MULTI_LINE":
            return [f"/*{node.value}*/"]
        if node.type == "INTEGER_LITERAL":
            return [str(int(node.value))]
        if node.type == "FLOATING_POINT_LITERAL":
            suffix = "d" if isinstance(node.value, IodxFloat64) else ""
            return [f"{_float_text(node.value)}{suffix}"]
        if node.type == "STRING_LITERAL_DQ":
            return [f'"{escape_double_quotes(str(node.value))}"']
        if node.type == "STRING_LITERAL_SQ":
            return [f"'{escape_single_quotes(str(node.value))}'"]
        if node.type in {"ANY_LITERAL", "ANY_OPERATOR", "ANY_SEPARATOR"}:
            return [_literal_text(node.value)]
        if node.type == "LEFT_PAREN":
            return ["("]
        if node.type == "RIGHT_PAREN":
            return [")"]
        if node.type == "WHITE_SPACE":
            return [" "]
        raise TypeError(f"Unsupported IODX CST node type: {node.type}")

    def _print_list(
        self,
        values: Sequence[Any],
        start_at: int,
        left: str | None,
        right: str | None,
        *,
        add_tabs: bool,
    ) -> list[str]:
        if (left is None) != (right is None):
            raise ValueError("left and right must either both be set or both be None")

        self._level += 1
        try:
            return self._print_list_at_current_level(
                values, start_at, left, right, add_tabs=add_tabs
            )
        finally:
            self._level -= 1

    def _print_list_at_current_level(
        self,
        values: Sequence[Any],
        start_at: int,
        left: str | None,
        right: str | None,
        *,
        add_tabs: bool,
    ) -> list[str]:
        rendered: list[str] = []
        common_length = 0
        try_compact = True

        for value in values:
            if _is_single_line_comment(value):
                try_compact = False
            child_lines = self._print_value(start_at + len(self.tab), value)
            if not child_lines:
                raise ValueError("An IODX value produced no output")
            rendered.extend(child_lines)
            if len(child_lines) > 1:
                try_compact = False
            else:
                common_length += len(child_lines[0])

        if try_compact and self._level >= self.compact_from_level:
            estimated_length = common_length + max(0, len(rendered) - 1)
            if left is not None and right is not None:
                estimated_length += len(left) + len(right)
            if (
                estimated_length + start_at <= self.max_width
                and estimated_length <= self.max_local_width
            ):
                body = " ".join(rendered)
                return [body if left is None else f"{left}{body}{right}"]

        if left is None or right is None:
            return [f"{self.tab}{line}" for line in rendered] if add_tabs else rendered
        if add_tabs:
            return [left, *(f"{self.tab}{line}" for line in rendered), right]
        return [left, *rendered, right]


def dumps(
    value: Any,
    *,
    max_width: int = 100,
    max_local_width: int = sys.maxsize,
    compact_from_level: int = 0,
    tab: str = "  ",
) -> str:
    """Serialize one syntax-model value to an IODX string."""

    return IodxPrinter(
        max_width=max_width,
        max_local_width=max_local_width,
        compact_from_level=compact_from_level,
        tab=tab,
    ).render(value)


def dumps_all(
    values: Sequence[Any],
    *,
    max_width: int = 100,
    max_local_width: int = sys.maxsize,
    compact_from_level: int = 0,
    tab: str = "  ",
) -> str:
    """Serialize top-level syntax-model values without an outer wrapper."""

    return IodxPrinter(
        max_width=max_width,
        max_local_width=max_local_width,
        compact_from_level=compact_from_level,
        tab=tab,
    ).render_all(values)


def dump(
    value: Any,
    stream: TextIO,
    *,
    max_width: int = 100,
    max_local_width: int = sys.maxsize,
    compact_from_level: int = 0,
    tab: str = "  ",
) -> None:
    """Serialize one syntax-model value to a text stream."""

    stream.write(
        dumps(
            value,
            max_width=max_width,
            max_local_width=max_local_width,
            compact_from_level=compact_from_level,
            tab=tab,
        )
    )


def dump_all(
    values: Sequence[Any],
    stream: TextIO,
    *,
    max_width: int = 100,
    max_local_width: int = sys.maxsize,
    compact_from_level: int = 0,
    tab: str = "  ",
) -> None:
    """Serialize top-level syntax-model values to a text stream."""

    stream.write(
        dumps_all(
            values,
            max_width=max_width,
            max_local_width=max_local_width,
            compact_from_level=compact_from_level,
            tab=tab,
        )
    )


def _float_text(value: float, *, compact_integer: bool = False) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("IODX does not support non-finite floating-point values")
    text = repr(number)
    if compact_integer and text.endswith(".0"):
        return text[:-2]
    return text


def _literal_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _is_single_line_comment(value: Any) -> bool:
    if isinstance(value, IodxComment):
        return value.single_line
    return isinstance(value, IodxCst) and value.type == "COMMENT_SINGLE_LINE"
