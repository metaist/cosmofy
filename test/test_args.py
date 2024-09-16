"""Test arg parsing."""

# std
from pathlib import Path
from shlex import split

# lib
import pytest

# pkg
from cosmofy.args import Args


def test_empty() -> None:
    """Empty args."""
    assert Args.parse([]) == Args()


def test_basic() -> None:
    """Basic flags."""
    assert Args.parse(
        split("--clone --args '-m foo' --output bar/baz src/repo")
    ) == Args(clone=True, args="-m foo", output=Path("bar/baz"), add=["src/repo"])


def test_disable_cache() -> None:
    """Disable cache."""
    assert Args.parse(split("--cache 0")) == Args(cache=None)
    assert Args.parse(split("--cache false")) == Args(cache=None)
    assert Args.parse(split("--cache False")) == Args(cache=None)
    assert Args.parse(split("--cache FALSE")) == Args(cache=None)


def test_bad_arg() -> None:
    """Bad or missing arg."""
    with pytest.raises(ValueError):
        Args.parse(["--unknown"])

    # missing
    with pytest.raises(ValueError):
        Args.parse(["--python-url"])

    with pytest.raises(ValueError):
        Args.parse(["--cache"])

    with pytest.raises(ValueError):
        Args.parse(["--add"])
