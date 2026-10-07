import pytest

from iodx import (
    Caret,
    IodxComment,
    IodxEntity,
    IodxEntityError,
    IodxField,
    IodxFloat32,
    IodxFloat64,
    IodxInt64,
    loads,
    loads_all,
)


def test_read_entity_structure() -> None:
    assert loads_all("") == []
    assert loads("()") == IodxEntity(None)
    assert loads("foo()") == IodxEntity("foo")
    assert loads("foo(bar)") == IodxEntity("foo", ["bar"])
    assert loads("foo(bar(hello))") == IodxEntity("foo", [IodxEntity("bar", ["hello"])])
    assert loads("foo(bar (hello))") == IodxEntity("foo", ["bar", IodxEntity(None, ["hello"])])


def test_read_fields_and_mixed_children() -> None:
    assert loads("(a=b e c=d f)") == IodxEntity(
        None,
        [IodxField("a", "b"), "e", IodxField("c", "d"), "f"],
    )
    assert loads("(null=value key=null true=false)") == IodxEntity(
        None,
        [
            IodxField(None, "value"),
            IodxField("key", None),
            IodxField(True, False),
        ],
    )
    assert loads("(a,b;c)") == IodxEntity(None, ["a", ",", "b", ";", "c"])


def test_empty_map_is_an_explicit_syntax_special_case() -> None:
    assert loads("(=)") == {}


def test_numeric_suffix_types_are_preserved() -> None:
    values = loads_all("42 42L 1.5 2f 3d")

    assert values == [42, 42, 1.5, 2.0, 3.0]
    assert type(values[0]) is int
    assert type(values[1]) is IodxInt64
    assert type(values[2]) is IodxFloat32
    assert type(values[3]) is IodxFloat32
    assert type(values[4]) is IodxFloat64


def test_entities_and_fields_preserve_source_ranges() -> None:
    person = loads('Person(name = "John"\nage = 25)')

    assert person.caret == Caret(1, 1, 2, 9, 0, 30)
    assert person.children_carets == [
        Caret(1, 8, 1, 20, 7, 20),
        Caret(2, 1, 2, 8, 21, 29),
    ]
    assert person.children[0].caret == person.children_carets[0]


def test_comments_are_first_class_values() -> None:
    values = loads_all("//header\nPerson('John') 42 /*tail*/")

    assert values == [
        IodxComment("header", True),
        IodxEntity("Person", ["John"]),
        42,
        IodxComment("tail", False),
    ]
    assert values[0].caret == Caret(1, 1, 1, 8, 0, 8)


@pytest.mark.parametrize(
    ("source", "message", "offset"),
    [
        ("(= a)", "Expected key before '=' at 1:2", 1),
        ("(a =)", "Expected value after '=' at 1:4", 3),
        ("(a = =)", "Expected value at 1:6", 5),
        ("(a = b = c)", "Expected key before '=' at 1:8", 7),
        ("(a//\n = b)", "Comment instead of key at 1:3", 2),
        ("(a = //\nb)", "Comment instead of value at 1:6", 5),
    ],
)
def test_invalid_fields_report_semantic_location(source: str, message: str, offset: int) -> None:
    with pytest.raises(IodxEntityError, match="^" + message.replace("=", "\\=")) as caught:
        loads(source)

    assert caught.value.caret is not None
    assert caught.value.caret.begin_offset == offset


@pytest.mark.parametrize(("source", "count"), [("", 0), ("a b", 2)])
def test_read_requires_exactly_one_value(source: str, count: int) -> None:
    with pytest.raises(IodxEntityError, match=f"Expected exactly one value, got {count}"):
        loads(source)


def test_entity_field_helpers() -> None:
    entity = IodxEntity("Config", [IodxField("width", 800), "visible"])

    assert entity.has_field("width")
    assert not entity.has_field("height")
    assert entity.get_field("width") == 800
    assert entity.get_field("height", 600) == 600
    assert entity.fields == [IodxField("width", 800)]
    assert entity.with_replaced("width", 1024).get_field("width") == 1024
