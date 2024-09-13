"""Test arg parsing."""

from cosmofy.args import Args


def test_empty() -> None:
    """Empty args."""
    assert Args.parse([]) == Args()
