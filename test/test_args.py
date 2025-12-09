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
    assert Args.parse(split("--args '-m foo' --output bar/baz -a src/repo")) == Args(
        args="-m foo", output=Path("bar/baz"), add=["src/repo"]
    )


def test_dry_run() -> None:
    """dry_run => for_real."""
    args = Args()
    assert not args.dry_run
    assert args.for_real

    args.for_real = False
    assert args.dry_run
    assert not args.for_real


def test_default_input() -> None:
    """Default input."""
    assert Args.parse(split("--input foo")) == Args(
        input=Path("foo"), output=Path("foo")
    )
    assert Args.parse(split("--cosmo")) == Args(cosmo=True)


def test_disable_cache() -> None:
    """Disable cache."""
    assert Args.parse(split("--no-cache")) == Args(no_cache=True)
    assert Args.parse(split("--cache-dir foo/baz")) == Args(cache_dir=Path("foo/baz"))
    assert Args.parse(split("--no-cache --cache-dir foo/baz")) == Args(
        no_cache=True, cache_dir=Path("foo/baz")
    )


def test_self_updater() -> None:
    """Self updater args."""
    release = "http://example.com/foo"
    receipt = "http://example.com/foo.json"
    assert Args.parse(split(f"--release-url {release}")) == Args(
        release_url=release, receipt_url=receipt
    )
    assert Args.parse(split(f"--receipt-url {receipt}")) == Args(
        release_url=release, receipt_url=receipt
    )
    with pytest.raises(ValueError):
        Args.parse(split("--release-version 0.1.0"))  # missing url


def test_bad_arg() -> None:
    """Bad or missing arg."""
    with pytest.raises(ValueError):
        Args.parse(["--unknown"])

    with pytest.raises(ValueError):
        Args.parse(["unknown"])

    # missing
    with pytest.raises(ValueError):
        Args.parse(["--python-url"])

    with pytest.raises(ValueError):
        Args.parse(["--cache-dir"])

    with pytest.raises(ValueError):
        Args.parse(["--add"])
