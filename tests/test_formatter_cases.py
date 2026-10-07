from pathlib import Path

from iodx import IodxField, dumps, loads, loads_all

CASES = Path(__file__).parent / "resources" / "upstream" / "formatting.cases.sql.style.iodx"
SETTING_NAMES = {
    "maxWidth": "max_width",
    "maxLocalWidth": "max_local_width",
    "compactFromLevel": "compact_from_level",
}


def test_upstream_formatter_cases_and_whitespace_variants() -> None:
    settings = {
        "max_width": 100,
        "max_local_width": 2**63 - 1,
        "compact_from_level": 0,
    }

    for item in loads_all(CASES.read_text(encoding="utf-8")):
        if isinstance(item, IodxField):
            settings[SETTING_NAMES[item.key]] = item.value
            continue
        if not isinstance(item, str):
            continue

        canonical = item
        assert _format(canonical, settings) == canonical
        assert _format(_replace_whitespace(canonical, " "), settings) == canonical
        assert _format(_replace_whitespace(canonical, "\n    "), settings) == canonical


def _format(source: str, settings: dict[str, int]) -> str:
    return "\n" + dumps(loads(source), **settings) + "\n"


def _replace_whitespace(text: str, replacement: str) -> str:
    result: list[str] = []
    state = "normal"
    index = 0

    while index < len(text):
        char = text[index]

        if state in {"single", "double"}:
            result.append(char)
            if char == "\\" and index + 1 < len(text):
                index += 1
                result.append(text[index])
            elif state == "single" and char == "'":
                state = "normal"
            elif state == "double" and char == '"':
                state = "normal"
            index += 1
            continue

        if state == "line_comment":
            result.append(char)
            if char in "\r\n":
                state = "normal"
            index += 1
            continue

        if state == "block_comment":
            result.append(char)
            if char == "*" and index + 1 < len(text) and text[index + 1] == "/":
                index += 1
                result.append("/")
                state = "normal"
            index += 1
            continue

        if char in {"'", '"'}:
            state = "single" if char == "'" else "double"
            result.append(char)
        elif text.startswith("//", index):
            state = "line_comment"
            result.append("//")
            index += 1
        elif text.startswith("/*", index):
            state = "block_comment"
            result.append("/*")
            index += 1
        elif char.isspace():
            while index + 1 < len(text) and text[index + 1].isspace():
                index += 1
            result.append(replacement)
        else:
            result.append(char)
        index += 1

    return "".join(result)
