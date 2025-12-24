# lib
import pytest

# pkg
from cosmofy.fs.add import sanitize_zip_path


def test_backslash() -> None:
    assert sanitize_zip_path("foo\\bar\\baz.py") == "foo/bar/baz.py"
    assert sanitize_zip_path("foo\\bar/baz.py") == "foo/bar/baz.py"


def test_leading_slash() -> None:
    assert sanitize_zip_path("/etc/passwd") == "etc/passwd"
    assert sanitize_zip_path("///foo/bar") == "foo/bar"
    assert sanitize_zip_path("foo/bar") == "foo/bar"


def test_path_traversal() -> None:
    with pytest.raises(ValueError):
        sanitize_zip_path("../etc/passwd")

    with pytest.raises(ValueError):
        sanitize_zip_path("foo/../bar")

    with pytest.raises(ValueError):
        sanitize_zip_path("foo/bar/..")

    assert sanitize_zip_path("foo/..bar") == "foo/..bar", "..bar != .."


def test_dot_removal() -> None:
    assert sanitize_zip_path("./foo/./bar") == "foo/bar"
    assert sanitize_zip_path(".") == ""


def test_empty_segments() -> None:
    assert sanitize_zip_path("foo//bar") == "foo/bar"
    assert sanitize_zip_path("foo///bar") == "foo/bar"


def test_edge_cases() -> None:
    assert sanitize_zip_path("") == ""
    assert sanitize_zip_path("/") == ""
