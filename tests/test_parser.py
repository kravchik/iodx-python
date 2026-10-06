from pathlib import Path

import pytest

from iodx import IodxParseError, IodxParser, parse


def test_parse_literals_with_native_python_values() -> None:
    document = parse("true false null word 42 -0xFF 9223372036854775808L 1.5 2d 3f")

    assert [child.type for child in document.children] == [
        "ANY_LITERAL",
        "ANY_LITERAL",
        "ANY_LITERAL",
        "ANY_LITERAL",
        "INTEGER_LITERAL",
        "INTEGER_LITERAL",
        "INTEGER_LITERAL",
        "FLOATING_POINT_LITERAL",
        "FLOATING_POINT_LITERAL",
        "FLOATING_POINT_LITERAL",
    ]
    assert [child.value for child in document.children] == [
        True,
        False,
        None,
        "word",
        42,
        -255,
        9223372036854775808,
        1.5,
        2.0,
        3.0,
    ]


def test_parse_named_class_preserves_structure_and_field_identity() -> None:
    clazz = IodxParser("Spell(rare 42)").parse_class()

    assert clazz.type == "NAMED_CLASS"
    assert [child.type for child in clazz.children] == [
        "ANY_LITERAL",
        "LEFT_PAREN",
        "LIST_BODY",
        "RIGHT_PAREN",
    ]
    assert clazz.child_by_field["name"] is clazz.children[0]
    assert clazz.child_by_field["body"] is clazz.children[2]
    assert clazz.children[1].value is None
    assert clazz.children[3].value is None
    assert [child.value for child in clazz.child_by_field["body"].children] == ["rare", 42]


def test_parse_unnamed_and_nested_classes() -> None:
    outer = IodxParser("(outer(inner(value)))").parse_class()
    outer_body = outer.child_by_field["body"]
    named_outer = outer_body.children[0]
    inner = named_outer.child_by_field["body"].children[0]

    assert outer.type == "UNNAMED_CLASS"
    assert named_outer.child_by_field["name"].value == "outer"
    assert inner.type == "NAMED_CLASS"
    assert inner.child_by_field["name"].value == "inner"
    assert inner.child_by_field["body"].children[0].value == "value"


def test_nested_body_positions_use_their_own_opening_parenthesis() -> None:
    outer = IodxParser("outer(inner(value))").parse_class()
    outer_body = outer.child_by_field["body"]
    inner_body = outer_body.children[0].child_by_field["body"]

    assert (outer_body.caret.begin_offset, outer_body.caret.end_offset) == (5, 18)
    assert (inner_body.caret.begin_offset, inner_body.caret.end_offset) == (11, 17)


def test_parse_comments_and_strings() -> None:
    document = parse(
        "// heading\n/*details*/ 'old\\sscroll' \"Say \\\"open\\\"\" "
        "'emoji: \\uD83D\\uDE00'"
    )

    assert [child.type for child in document.children] == [
        "COMMENT_SINGLE_LINE",
        "COMMENT_MULTI_LINE",
        "STRING_LITERAL_SQ",
        "STRING_LITERAL_DQ",
        "STRING_LITERAL_SQ",
    ]
    assert [child.value for child in document.children] == [
        " heading",
        "details",
        "old scroll",
        'Say "open"',
        "emoji: 😀",
    ]


def test_single_line_comment_at_eof_excludes_internal_parser_suffix() -> None:
    comment = parse("// no newline").children[0]

    assert comment.value == " no newline"
    assert comment.caret.end_offset == len("// no newline")


def test_multiline_positions_refer_to_original_source() -> None:
    source = "\n  'x\\u0041y'"
    string = parse(source).children[0]

    assert string.value == "xAy"
    assert string.caret.begin_line == 2
    assert string.caret.begin_column == 3
    assert string.caret.begin_offset == 3
    assert string.caret.end_offset == len(source)


@pytest.mark.parametrize("source", ["", " ", "\n\t"])
def test_empty_document(source: str) -> None:
    document = parse(source)

    assert document.children == []
    assert document.caret.begin_offset == 0
    assert document.caret.end_offset == len(source)


def test_source_is_never_treated_as_a_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "existing.iodx").write_text("wrong", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    document = parse("existing.iodx")

    assert document.children[0].value == "existing.iodx"


@pytest.mark.parametrize(
    "source",
    [
        "012",
        "0x",
        "hello)",
        "(",
        "valid\nvalid\n(incomplete",
    ],
)
def test_invalid_or_incomplete_documents_are_rejected(source: str) -> None:
    with pytest.raises(IodxParseError) as caught:
        parse(source)

    assert caught.value.caret is not None


def test_parse_class_rejects_standalone_literal() -> None:
    with pytest.raises(IodxParseError, match="Expected a class") as caught:
        IodxParser("plain").parse_class()

    assert caught.value.caret is not None
    assert (caught.value.caret.begin_offset, caught.value.caret.end_offset) == (0, 5)


@pytest.mark.parametrize(
    ("source", "offset", "length", "message"),
    [
        (r"'bad\u12'", 4, 4, "Incomplete Unicode escape"),
        (r"'bad\u12G4'", 4, 6, "Invalid hexadecimal digit"),
        (r"'bad\uD83D'", 4, 6, "High surrogate"),
        (r"'bad\uDE00'", 4, 6, "Unexpected low surrogate"),
        (r"'bad\q'", 4, 2, "Unknown escape symbol"),
    ],
)
def test_string_errors_have_absolute_source_ranges(
    source: str, offset: int, length: int, message: str
) -> None:
    with pytest.raises(IodxParseError, match=message) as caught:
        parse(source)

    assert caught.value.caret is not None
    assert caught.value.caret.begin_offset == offset
    assert caught.value.caret.end_offset == offset + length
