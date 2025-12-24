# pkg
from cosmofy.fs import expand_glob


def test_with_wildcards() -> None:
    assert list(expand_glob(["foo.py", "bar.py", "baz.txt"], "*.py")) == [
        "foo.py",
        "bar.py",
    ]

    assert list(expand_glob(["Lib/a.py", "Lib/b/c.py"], "Lib/*")) == ["Lib/a.py"]

    assert list(expand_glob(["Lib/a.py", "Lib/b/c.py"], "Lib/**")) == [
        "Lib/a.py",
        "Lib/b/c.py",
    ]


def test_without_wildcards() -> None:
    assert list(expand_glob(["foo.py", "bar.py"], "baz.py")) == ["baz.py"]
    assert list(expand_glob([], "foo.py")) == ["foo.py"]


def test_empty() -> None:
    assert list(expand_glob(["foo.txt", "bar.txt"], "*.py")) == []
