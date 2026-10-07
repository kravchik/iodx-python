# IODX for Python

Python implementation of [IODX](https://iodx.org/), a compact, human-readable
syntax for structured data, configs, fixtures, serialization, and data exchange.

This implementation is under development. The language-independent grammar lives
in the main [IODX repository](https://github.com/kravchik/iodx).

## Usage

Parse text into a concrete syntax tree with `parse`, or deserialize the higher-level
syntax model with `loads` and `loads_all`:

```python
from iodx import IodxEntity, IodxField, dumps, loads

scroll = loads('SpellScroll(title = "Whisper" charges = 3)')

assert isinstance(scroll, IodxEntity)
assert scroll.name == "SpellScroll"
assert scroll.children == [
    IodxField("title", "Whisper"),
    IodxField("charges", 3),
]

text = dumps(scroll, max_width=40)
```

Use `load` and `dump` with text streams. Their `*_all` variants handle multiple
top-level values:

```python
from iodx import dump, load

with open("scroll.iodx", encoding="utf-8") as source:
    scroll = load(source)

with open("scroll.iodx", "w", encoding="utf-8") as target:
    dump(scroll, target, max_width=40)
```

The syntax model retains named and unnamed entities, fields, comments, and source
ranges. `IodxPrinter` additionally exposes `max_width`, `max_local_width`,
`compact_from_level`, and `tab` formatting settings through its `render` and
`render_all` methods. Mapping syntax values to Python classes is not implemented
yet.

## Development

Create a virtual environment and install the package with its development tools:

```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install --editable ".[dev]"
pytest
```

The package uses the standard `src` layout and is built from `pyproject.toml`.
Parser generation is a separate development step; installing or using the package
will not require Java or Maven.

## Parser generation

CongoCC grammar shared with the Java implementation and its `.iodx` test fixtures
are mirrored from a sibling `iodx` checkout. Synchronize or verify them with:

```shell
scripts/sync-from-java.sh
scripts/sync-from-java.sh --check
```

Set `IODX_SOURCE_ROOT` if the Java repository is not located at `../iodx` relative
to this repository. The copied files remain committed, so normal builds and tests
do not depend on the sibling checkout.

CongoCC itself runs on the JVM. Regenerate the parser from the repository root with:

```shell
mvn -f codegen/pom.xml clean generate-sources
```

The Maven wrapper lives under `codegen/`, separate from the Python build. Generated
Python files are committed under `src/iodx/_generatedparser`, so installing, using,
and releasing the package remain Python-native and do not require Java or Maven.

## License

[MIT](LICENSE)
