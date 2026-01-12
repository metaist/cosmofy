"""Test self update command."""

# std
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch

# lib

# pkg
from cosmofy import baton
from cosmofy.self.update import Args
from cosmofy.self.update import run


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split(""))
    assert args.help is False
    assert args.dry_run is False


def test_arg_parsing_dry_run() -> None:
    """Test Args parsing with --dry-run."""
    args = baton.parse(Args, split("--dry-run"))
    assert args.dry_run is True


@patch("cosmofy.self.update.is_zipfile")
def test_run_not_zipfile(mock_is_zipfile: MagicMock) -> None:
    """Test run fails when not running from zipfile."""
    mock_is_zipfile.return_value = False

    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 2


@patch("cosmofy.self.update.self_update")
@patch("cosmofy.self.update.is_zipfile")
def test_run_success(mock_is_zipfile: MagicMock, mock_self_update: MagicMock) -> None:
    """Test run succeeds when running from zipfile."""
    mock_is_zipfile.return_value = True
    mock_self_update.return_value = None

    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 0
    mock_self_update.assert_called_once()


@patch("cosmofy.self.update.self_update")
@patch("cosmofy.self.update.is_zipfile")
def test_run_update_error(
    mock_is_zipfile: MagicMock, mock_self_update: MagicMock
) -> None:
    """Test run handles update errors."""
    mock_is_zipfile.return_value = True
    mock_self_update.side_effect = RuntimeError("Update failed")

    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 2
