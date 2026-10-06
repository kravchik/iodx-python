import iodx


def test_package_imports() -> None:
    assert iodx.__name__ == "iodx"
    assert iodx.Caret.__module__ == "iodx.caret"
    assert iodx.IodxCst.__module__ == "iodx.cst"
