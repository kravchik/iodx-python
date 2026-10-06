from pathlib import Path

import pytest

from iodx import parse

UPSTREAM_FIXTURES = Path(__file__).parent / "resources" / "upstream"
UPSTREAM_FIXTURE_PATHS = sorted(UPSTREAM_FIXTURES.glob("*.iodx"))

if not UPSTREAM_FIXTURE_PATHS:
    raise RuntimeError(f"No synchronized IODX fixtures found in {UPSTREAM_FIXTURES}")


@pytest.mark.parametrize(
    "path",
    UPSTREAM_FIXTURE_PATHS,
    ids=lambda path: path.name,
)
def test_upstream_iodx_document_parses(path: Path) -> None:
    parse(path.read_text(encoding="utf-8"))
