"""End-to-end tests."""

# std
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch

# pkg
from cosmofy import main


def test_arg_bad() -> None:
    """Bad args."""
    assert main(split("cosmofy")) != 0, "missing paths"
    assert main(split("cosmofy --unknown")) != 0, "unknown arg"
    assert main(split("cosmofy src/cosmofy --clone")) != 0, "--clone without --cosmo"


def test_arg_general() -> None:
    """General args."""
    assert main(split("cosmofy --debug --version")) == 0, "--version"
    assert main(split("cosmofy --debug --help")) == 0, "--help"


@patch("cosmofy.Bundler.run")
def test_run(_run: MagicMock) -> None:
    """Run the bundler."""
    assert main(split("cosmofy src/cosmofy --dry-run")) == 0
    _run.assert_called_once()
