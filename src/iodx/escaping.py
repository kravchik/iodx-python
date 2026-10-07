from __future__ import annotations

from collections.abc import Mapping


class IodxEscapeError(ValueError):
    """An invalid IODX escape sequence with its source range."""

    def __init__(self, message: str, offset: int, length: int) -> None:
        super().__init__(message)
        self.offset = offset
        self.length = max(1, length)


_COMMON_ESCAPES = {
    "\t": "t",
    "\b": "b",
    "\r": "r",
    "\f": "f",
    "\\": "\\",
}
_DOUBLE_QUOTE_ESCAPES = {**_COMMON_ESCAPES, '"': '"'}
_SINGLE_QUOTE_ESCAPES = {**_COMMON_ESCAPES, "'": "'"}
_UNESCAPES = {
    **{escaped: raw for raw, escaped in _COMMON_ESCAPES.items()},
    "n": "\n",
    "s": " ",
    '"': '"',
    "'": "'",
}


def unescape_quoted(value: str) -> str:
    """Remove matching quotes and decode IODX escape sequences."""

    if len(value) < 2 or value[0] not in {'"', "'"} or value[-1] != value[0]:
        raise IodxEscapeError("Expected a quoted string", 0, len(value))
    return unescape(value[1:-1])


def unescape_double_quotes(value: str) -> str:
    return unescape_quoted(value)


def unescape_single_quotes(value: str) -> str:
    return unescape_quoted(value)


def unescape(value: str) -> str:
    result: list[str] = []
    offset = 0

    while offset < len(value):
        char = value[offset]
        if char == "\r":
            offset += 1
            continue

        if char == "\\":
            escape_offset = offset
            offset += 1
            if offset >= len(value):
                raise IodxEscapeError("Uncompleted escape sequence", escape_offset, 1)

            escape_symbol = value[offset]
            if escape_symbol == "u":
                code_unit = _parse_unicode_escape(value, escape_offset)
                offset = escape_offset + 6

                if _is_high_surrogate(code_unit):
                    low_offset = offset
                    if not _starts_unicode_escape(value, low_offset):
                        raise IodxEscapeError(
                            "High surrogate must be followed by a low surrogate escape",
                            escape_offset,
                            6,
                        )
                    low_surrogate = _parse_unicode_escape(value, low_offset)
                    if not _is_low_surrogate(low_surrogate):
                        raise IodxEscapeError("Expected a low surrogate escape", low_offset, 6)
                    result.append(chr(_combine_surrogates(code_unit, low_surrogate)))
                    offset = low_offset + 6
                    continue

                if _is_low_surrogate(code_unit):
                    raise IodxEscapeError("Unexpected low surrogate", escape_offset, 6)

                result.append(chr(code_unit))
                continue

            decoded = _UNESCAPES.get(escape_symbol)
            if decoded is None:
                raise IodxEscapeError(f"Unknown escape symbol: {escape_symbol}", escape_offset, 2)
            result.append(decoded)
            offset += 1
            continue

        code_point = ord(char)
        if _is_high_surrogate(code_point):
            if offset + 1 >= len(value):
                raise IodxEscapeError("Lone high surrogate", offset, 1)
            low_surrogate = ord(value[offset + 1])
            if not _is_low_surrogate(low_surrogate):
                raise IodxEscapeError("Lone high surrogate", offset, 1)
            result.append(chr(_combine_surrogates(code_point, low_surrogate)))
            offset += 2
            continue
        if _is_low_surrogate(code_point):
            raise IodxEscapeError("Lone low surrogate", offset, 1)

        result.append(char)
        offset += 1

    return "".join(result)


def escape_double_quotes(value: str) -> str:
    return _escape(value, _DOUBLE_QUOTE_ESCAPES)


def escape_single_quotes(value: str) -> str:
    return _escape(value, _SINGLE_QUOTE_ESCAPES)


def _escape(value: str, escapes: Mapping[str, str]) -> str:
    result: list[str] = []
    offset = 0

    while offset < len(value):
        char = value[offset]
        code_point = ord(char)

        if _is_high_surrogate(code_point):
            if offset + 1 >= len(value):
                raise ValueError(f"Lone high surrogate at offset {offset}")
            low_surrogate = ord(value[offset + 1])
            if not _is_low_surrogate(low_surrogate):
                raise ValueError(f"Lone high surrogate at offset {offset}")
            result.append(chr(_combine_surrogates(code_point, low_surrogate)))
            offset += 2
            continue
        if _is_low_surrogate(code_point):
            raise ValueError(f"Lone low surrogate at offset {offset}")

        escaped = escapes.get(char)
        if escaped is not None:
            result.extend(("\\", escaped))
        elif char != "\n" and _is_iso_control(code_point):
            result.append(f"\\u{code_point:04X}")
        else:
            result.append(char)
        offset += 1

    return "".join(result)


def _starts_unicode_escape(value: str, offset: int) -> bool:
    return offset + 1 < len(value) and value[offset : offset + 2] == "\\u"


def _parse_unicode_escape(value: str, offset: int) -> int:
    available_length = len(value) - offset
    if available_length < 6:
        raise IodxEscapeError("Incomplete Unicode escape", offset, available_length)

    digits = value[offset + 2 : offset + 6]
    if any(char not in "0123456789abcdefABCDEF" for char in digits):
        raise IodxEscapeError("Invalid hexadecimal digit in Unicode escape", offset, 6)
    return int(digits, 16)


def _is_high_surrogate(code_point: int) -> bool:
    return 0xD800 <= code_point <= 0xDBFF


def _is_low_surrogate(code_point: int) -> bool:
    return 0xDC00 <= code_point <= 0xDFFF


def _combine_surrogates(high: int, low: int) -> int:
    return 0x10000 + ((high - 0xD800) << 10) + (low - 0xDC00)


def _is_iso_control(code_point: int) -> bool:
    return code_point <= 0x1F or 0x7F <= code_point <= 0x9F
