from iodx import Caret, IodxCst


def test_caret_normalizes_zero_based_default_position() -> None:
    caret = Caret(0, 0, 2, 7, 0, 10)

    assert caret.begin_line == 1
    assert caret.begin_column == 1
    assert caret.format_begin() == "1:1"
    assert str(caret) == "1:1 .. 2:7 [0-10]"


def test_caret_combines_start_and_end_ranges() -> None:
    start = Caret(2, 3, 2, 5, 4, 6)
    end = Caret(4, 7, 4, 9, 20, 22)

    assert Caret.start_end(start, end) == Caret(2, 3, 4, 9, 4, 22)


def test_cst_collections_are_not_shared() -> None:
    first = IodxCst("FIRST", None)
    second = IodxCst("SECOND", None)

    first.children.append(IodxCst("CHILD", None))
    first.child_by_field["child"] = first.children[0]

    assert second.children == []
    assert second.child_by_field == {}


def test_cst_string_representation_shows_structure() -> None:
    leaf = IodxCst("ANY_LITERAL", None, "value")
    root = IodxCst("LIST_BODY", None, children=[leaf])

    assert str(leaf) == "ANY_LITERAL"
    assert str(root) == "LIST_BODY([ANY_LITERAL])"
