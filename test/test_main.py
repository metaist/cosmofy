"""End-to-end tests."""

# std
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch

# pkg
from cosmofy.__main__ import main


def test_arg_bad() -> None:
    """Bad args."""
    assert main(split("cosmofy --unknown")) != 0, "unknown arg"


def test_arg_general() -> None:
    """General args."""
    assert main(split("cosmofy --version")) == 0, "--version"
    assert main(split("cosmofy --quiet --version")) == 0, "--version"
    assert main(split("cosmofy --verbose --help")) == 0, "--help"


@patch("cosmofy.__main__.Bundler.run")
def test_run(_run: MagicMock) -> None:
    """Run the bundler."""
    assert main(split("cosmofy --dry-run -vv")) == 0
    _run.assert_called_once()
