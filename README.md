# IODX for Python

Python implementation of [IODX](https://iodx.org/), a compact, human-readable
syntax for structured data, configs, fixtures, serialization, and data exchange.

This implementation is under development. The language-independent grammar lives
in the main [IODX repository](https://github.com/kravchik/iodx).

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
