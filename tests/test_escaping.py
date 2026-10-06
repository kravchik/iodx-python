import pytest

from iodx import (
    IodxEscapeError,
    escape_double_quotes,
    escape_single_quotes,
    unescape,
    unescape_quoted,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (r"\t\b\r\f\\", "\t\b\r\f\\"),
        (r"\n\s\"\'", "\n \"'"),
        (r"\u0041\u0416\u00e9", "AЖé"),
        (r"\uD83D\uDE00", "😀"),
        ("first\r\nsecond", "first\nsecond"),
    ],
)
def test_unescape_supported_sequences(source: str, expected: str) -> None:
    assert unescape(source) == expected


def test_unescape_quoted_accepts_both_quote_styles() -> None:
    assert unescape_quoted(r"'Don\'t'") == "Don't"
    assert unescape_quoted(r'"Say \"hello\""') == 'Say "hello"'


@pytest.mark.parametrize("source", ["", "plain", "'mismatch\""])
def test_unescape_quoted_rejects_missing_or_mismatched_quotes(source: str) -> None:
    with pytest.raises(IodxEscapeError, match="Expected a quoted string"):
        unescape_quoted(source)


@pytest.mark.parametrize(
    ("source", "offset", "length", "message"),
    [
        ("\\", 0, 1, "Uncompleted escape sequence"),
        (r"\q", 0, 2, "Unknown escape symbol: q"),
        (r"\u12", 0, 4, "Incomplete Unicode escape"),
        (r"\u12G4", 0, 6, "Invalid hexadecimal digit"),
        (r"\uD83D", 0, 6, "High surrogate"),
        (r"\uDE00", 0, 6, "Unexpected low surrogate"),
        (r"\uD83D\u0041", 6, 6, "Expected a low surrogate"),
    ],
)
def test_unescape_reports_precise_errors(
    source: str, offset: int, length: int, message: str
) -> None:
    with pytest.raises(IodxEscapeError, match=message) as caught:
        unescape(source)

    assert caught.value.offset == offset
    assert caught.value.length == length


def test_raw_surrogate_pair_is_normalized() -> None:
    assert unescape("\ud83d\ude00") == "😀"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("\ud800", "Lone high surrogate"),
        ("\udc00", "Lone low surrogate"),
    ],
)
def test_raw_lone_surrogates_are_rejected(source: str, message: str) -> None:
    with pytest.raises(IodxEscapeError, match=message):
        unescape(source)


def test_escape_uses_canonical_short_and_unicode_sequences() -> None:
    value = "\t\b\r\f\x00\x01\x7f\x85\nЖ 😀"

    assert escape_single_quotes(value) == r"\t\b\r\f\u0000\u0001\u007F\u0085" + "\nЖ 😀"


def test_escape_only_quotes_the_selected_delimiter() -> None:
    assert escape_single_quotes("'\"") == "\\'\""
    assert escape_double_quotes("'\"") == "'\\\""


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("\ud800", "Lone high surrogate at offset 0"),
        ("\udc00", "Lone low surrogate at offset 0"),
    ],
)
def test_escape_rejects_lone_surrogates(source: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        escape_single_quotes(source)
