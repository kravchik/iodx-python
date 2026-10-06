from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ._generatedparser import ParseException as _GeneratedParseException
from ._generatedparser import Parser as _GeneratedParser
from .caret import Caret
from .cst import IodxCst
from .errors import IodxParseError
from .escaping import IodxEscapeError, unescape_quoted

_RawNode = Mapping[str, Any]


class IodxParser:
    """Parse IODX source text into a concrete syntax tree."""

    def __init__(self, source: str) -> None:
        self.source = source
        # CongoCC's Python runtime treats an empty string as missing input and an
        # existing path as a filename. A trailing newline makes input textual in
        # both cases and safely terminates // comments; converted ranges are clamped
        # back to the original source.
        self._generated = _GeneratedParser(source + "\n")

    def parse_document(self) -> IodxCst:
        return self._parse(self._generated.parse_parseDocument)

    def parse_list_body(self) -> IodxCst:
        return self._parse(self._generated.parse_parseListBody)

    def parse_class(self) -> IodxCst:
        return self._parse(self._generated.parse_parseClass)

    def _parse(self, production: Callable[[], _RawNode]) -> IodxCst:
        try:
            raw = production()
        except _GeneratedParseException as error:
            raise self._syntax_error(error) from error
        return self._convert_node(raw, {})

    def _convert_node(self, raw: _RawNode, memo: dict[int, IodxCst]) -> IodxCst:
        existing = memo.get(id(raw))
        if existing is not None:
            return existing

        caret = self._raw_caret(raw)
        try:
            value = _convert_value(raw["type"], raw["value"])
        except IodxEscapeError as error:
            raise self._escape_error(caret, error) from error

        node = IodxCst(type=raw["type"], caret=caret, value=value)
        memo[id(raw)] = node
        node.children.extend(self._convert_node(child, memo) for child in raw["children"])
        node.child_by_field.update(
            (name, self._convert_node(child, memo)) for name, child in raw["fields"].items()
        )
        return node

    def _raw_caret(self, raw: _RawNode) -> Caret:
        begin_offset = min(raw["beginOffset"], len(self.source))
        end_offset = min(raw["endOffset"], len(self.source))
        begin_line, begin_column = self._position(begin_offset)
        if end_offset > begin_offset:
            end_line, end_column = self._position(end_offset - 1)
        else:
            end_line, end_column = begin_line, begin_column
        return Caret(
            begin_line,
            begin_column,
            end_line,
            end_column,
            begin_offset,
            end_offset,
        )

    def _syntax_error(self, error: _GeneratedParseException) -> IodxParseError:
        token = error.token
        caret = None
        if token is not None:
            begin_offset = min(token.begin_offset, len(self.source))
            end_offset = min(token.end_offset, len(self.source))
            begin_line, begin_column = self._position(begin_offset)
            if end_offset > begin_offset:
                end_line, end_column = self._position(end_offset - 1)
            else:
                end_line, end_column = begin_line, begin_column
            caret = Caret(
                begin_line,
                begin_column,
                end_line,
                end_column,
                begin_offset,
                end_offset,
            )

        message = error.args[0] if error.args and error.args[0] else str(error)
        return IodxParseError(message, caret)

    def _escape_error(self, token_caret: Caret, error: IodxEscapeError) -> IodxParseError:
        begin_offset = token_caret.begin_offset + 1 + error.offset
        content_end = max(token_caret.begin_offset + 1, token_caret.end_offset - 1)
        end_offset = min(content_end, begin_offset + error.length)
        end_offset = max(begin_offset + 1, end_offset)
        begin_line, begin_column = self._position(begin_offset)
        end_line, end_column = self._position(end_offset - 1)
        caret = Caret(
            begin_line,
            begin_column,
            end_line,
            end_column,
            begin_offset,
            end_offset,
        )
        return IodxParseError(f"{error} at offset {begin_offset}", caret)

    def _position(self, offset: int) -> tuple[int, int]:
        offset = max(0, min(offset, len(self.source)))
        line = self.source.count("\n", 0, offset) + 1
        line_start = self.source.rfind("\n", 0, offset) + 1
        return line, offset - line_start + 1


def parse(source: str) -> IodxCst:
    """Parse a complete IODX document."""

    return IodxParser(source).parse_document()


def _convert_value(node_type: str, raw_value: Any) -> Any:
    if node_type == "INTEGER_LITERAL":
        text = raw_value[:-1] if raw_value[-1] in "lL" else raw_value
        return int(text, 0)
    if node_type == "FLOATING_POINT_LITERAL":
        text = raw_value[:-1] if raw_value[-1] in "fFdD" else raw_value
        return float(text)
    if node_type in {"STRING_LITERAL_DQ", "STRING_LITERAL_SQ"}:
        return unescape_quoted(raw_value)
    if node_type == "COMMENT_SINGLE_LINE":
        return raw_value[2:]
    if node_type == "COMMENT_MULTI_LINE":
        return raw_value[2:-2]
    if node_type == "ANY_LITERAL":
        if raw_value == "true":
            return True
        if raw_value == "false":
            return False
        if raw_value == "null":
            return None
    return raw_value
