from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TextIO

from .caret import Caret
from .cst import IodxCst
from .entity import IodxComment, IodxEntity, IodxField
from .errors import IodxEntityError
from .parser import parse


def loads(source: str) -> Any:
    """Deserialize exactly one top-level IODX syntax value from a string."""

    values = loads_all(source)
    if len(values) != 1:
        raise IodxEntityError(f"Expected exactly one value, got {len(values)}")
    return values[0]


def loads_all(source: str) -> list[Any]:
    """Deserialize all top-level IODX syntax values from a string."""

    return resolve_nodes(parse(source).children)[0]


def load(stream: TextIO) -> Any:
    """Deserialize exactly one top-level IODX syntax value from a text stream."""

    return loads(stream.read())


def load_all(stream: TextIO) -> list[Any]:
    """Deserialize all top-level IODX syntax values from a text stream."""

    return loads_all(stream.read())


def resolve(node: IodxCst) -> Any:
    """Convert one CST node into a syntax-model value."""

    if node.type == "LIST_BODY":
        return resolve_nodes(node.children)[0]
    if node.type in {"NAMED_CLASS", "UNNAMED_CLASS"}:
        body = node.child_by_field["body"]
        if node.type == "UNNAMED_CLASS" and _is_empty_map(body.children):
            return {}
        name = None
        if node.type == "NAMED_CLASS":
            name = _entity_name(node.child_by_field["name"].value)
        children, child_carets = resolve_nodes(body.children)
        return IodxEntity(name, children, node.caret, child_carets)
    if node.type == "COMMENT_SINGLE_LINE":
        return IodxComment(str(node.value), True, node.caret)
    if node.type == "COMMENT_MULTI_LINE":
        return IodxComment(str(node.value), False, node.caret)
    if node.type in {
        "INTEGER_LITERAL",
        "FLOATING_POINT_LITERAL",
        "STRING_LITERAL_DQ",
        "STRING_LITERAL_SQ",
        "ANY_LITERAL",
        "ANY_OPERATOR",
        "ANY_SEPARATOR",
    }:
        return node.value
    raise IodxEntityError(f"Unknown IODX CST node type: {node.type}", node.caret)


def resolve_nodes(nodes: Sequence[IodxCst]) -> tuple[list[Any], list[Caret | None]]:
    """Resolve nodes and combine ``key = value`` triples into fields."""

    values: list[Any] = []
    carets: list[Caret | None] = []
    left_node: IodxCst | None = None
    index = 0

    while index < len(nodes):
        node = nodes[index]
        if not _is_delimiter(node):
            left_node = node
            values.append(resolve(node))
            carets.append(node.caret)
            index += 1
            continue

        if left_node is None:
            raise _entity_error("Expected key before '='", node)
        if _is_comment(left_node):
            raise _entity_error("Comment instead of key", left_node)

        index += 1
        if index >= len(nodes):
            raise _entity_error("Expected value after '='", node)
        right_node = nodes[index]
        if _is_comment(right_node):
            raise _entity_error("Comment instead of value", right_node)
        if _is_delimiter(right_node):
            raise _entity_error("Expected value", right_node)

        field_caret = _combine_carets(left_node.caret, right_node.caret)
        values[-1] = IodxField(values[-1], resolve(right_node), field_caret)
        carets[-1] = field_caret
        left_node = None
        index += 1

    return values, carets


def _entity_error(message: str, node: IodxCst) -> IodxEntityError:
    location = f" at {node.caret.format_begin()}" if node.caret is not None else ""
    return IodxEntityError(message + location, node.caret)


def _combine_carets(left: Caret | None, right: Caret | None) -> Caret | None:
    if left is None:
        return None
    if right is None:
        return left
    return Caret.start_end(left, right)


def _is_delimiter(node: IodxCst) -> bool:
    return node.type == "ANY_OPERATOR" and node.value == "="


def _is_comment(node: IodxCst) -> bool:
    return node.type in {"COMMENT_SINGLE_LINE", "COMMENT_MULTI_LINE"}


def _is_empty_map(nodes: Sequence[IodxCst]) -> bool:
    return len(nodes) == 1 and _is_delimiter(nodes[0])


def _entity_name(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    return str(value)
