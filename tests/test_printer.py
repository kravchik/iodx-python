from io import StringIO

import pytest

from iodx import (
    IodxComment,
    IodxEntity,
    IodxField,
    IodxFloat32,
    IodxFloat64,
    IodxInt64,
    IodxPrinter,
    dump,
    dump_all,
    dumps,
    dumps_all,
    load,
    load_all,
    loads,
    loads_all,
    parse,
)


@pytest.mark.parametrize("value", ["hello", "+", "==", ",", ";"])
def test_safe_standalone_tokens_do_not_need_quotes(value: str) -> None:
    assert IodxPrinter().without_quotes(value)


@pytest.mark.parametrize(
    "value",
    ["", "hello world", "true", "false", "null", "42", "3.14", "=", "//x", "/*x*/"],
)
def test_ambiguous_or_structural_strings_need_quotes(value: str) -> None:
    assert not IodxPrinter().without_quotes(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (42, "42"),
        (IodxInt64(42), "42l"),
        (IodxFloat32(3.14), "3.14f"),
        (IodxFloat32(3.0), "3f"),
        (IodxFloat64(2.71), "2.71d"),
        (2.0, "2d"),
        ("hello", "hello"),
        ("hello world", "'hello world'"),
        ("can't", '"can\'t"'),
        ("null", "'null'"),
    ],
)
def test_dumps_primitive_values(value: object, expected: str) -> None:
    assert dumps(value) == expected


def test_dumps_entities_fields_comments_and_collections() -> None:
    assert dumps(IodxEntity(None, [1, 2, 3])) == "(1 2 3)"
    assert dumps(IodxEntity("Vec2", ["x", "y"])) == "Vec2(x y)"
    assert dumps(IodxField("count", 42)) == "count = 42"
    assert dumps([]) == "()"
    assert dumps({}) == "(=)"
    assert dumps({"key": "value", "count": 42}) == "(key = value count = 42)"
    assert dumps(IodxComment(" generated", True)) == "// generated"
    assert dumps(IodxComment(" generated ", False)) == "/* generated */"


def test_single_line_comment_forces_multiline_layout() -> None:
    value = IodxEntity(None, [42, IodxComment(" comment"), "hello"])

    assert dumps(value) == "(\n  42\n  // comment\n  hello\n)"


def test_dumps_all_omits_outer_wrapper() -> None:
    assert dumps_all([IodxEntity("hello", ["world"]), None]) == "hello(world) null"


def test_stream_api_and_direct_renderer() -> None:
    value = IodxEntity("hello", ["world"])
    output = StringIO()

    dump(value, output)
    assert output.getvalue() == "hello(world)"
    assert load(StringIO(output.getvalue())) == value

    output = StringIO()
    dump_all([value, None], output)
    assert output.getvalue() == "hello(world) null"
    assert load_all(StringIO(output.getvalue())) == [value, None]

    printer = IodxPrinter(max_width=1)
    assert printer.render(value) == "hello(\n  world\n)"
    assert printer.render_all([value, None]) == "hello(\n  world\n)\nnull"


def test_cst_printing_normalizes_without_resolving_entities() -> None:
    assert dumps(parse("// comment")) == "// comment"
    assert dumps(parse("/* comment */")) == "/* comment */"
    assert dumps(parse('Spell("hello world" 2d)')) == 'Spell("hello world" 2.0d)'


@pytest.mark.parametrize(
    "source",
    [
        "()",
        "foo(bar)",
        "(a = b e c = d)",
        "/*comment*/",
        "'hello world'",
        "(=)",
        "Person(name = 'John' age = 25)",
    ],
)
def test_syntax_model_round_trip(source: str) -> None:
    value = loads(source)

    assert loads(dumps(value)) == value


def test_numeric_types_round_trip_through_entity_printer() -> None:
    values = loads_all("1 2L 3.5 4f 5d")

    result = loads_all(dumps_all(values))

    assert [type(value) for value in result] == [
        int,
        IodxInt64,
        IodxFloat32,
        IodxFloat32,
        IodxFloat64,
    ]


def test_width_and_compaction_settings() -> None:
    value = loads("outer(inner(1))")

    assert dumps(value, compact_from_level=1) == "outer(inner(1))"
    assert dumps(value, compact_from_level=2) == "outer(\n  inner(1)\n)"
    assert dumps(value, max_width=1) == "outer(\n  inner(\n    1\n  )\n)"
    assert dumps(IodxEntity(None, [1, 2]), tab="\t", max_width=1) == "(\n\t1\n\t2\n)"


def test_unsupported_values_and_non_finite_floats_are_rejected() -> None:
    with pytest.raises(TypeError, match="Unsupported IODX value type"):
        dumps(object())
    with pytest.raises(ValueError, match="non-finite"):
        dumps(float("inf"))
