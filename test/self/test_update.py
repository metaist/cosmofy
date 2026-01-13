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


@patch("cosmofy.self.update.download_release")
@patch("cosmofy.self.update.check")
@patch("cosmofy.self.update.zipfile.ZipFile")
@patch("cosmofy.self.update.is_zipfile")
def test_run_success(
    mock_is_zipfile: MagicMock,
    mock_zipfile: MagicMock,
    mock_check: MagicMock,
    mock_download: MagicMock,
) -> None:
    """Test run succeeds when running from zipfile."""
    mock_is_zipfile.return_value = True
    mock_local = MagicMock(version="1.0.0")
    mock_remote = MagicMock(version="1.0.0", release_url="", hash="", algo="")
    mock_check.return_value = (False, mock_local, mock_remote)

    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 0


@patch("cosmofy.self.update.download_release")
@patch("cosmofy.self.update.check")
@patch("cosmofy.self.update.zipfile.ZipFile")
@patch("cosmofy.self.update.is_zipfile")
def test_run_with_update(
    mock_is_zipfile: MagicMock,
    mock_zipfile: MagicMock,
    mock_check: MagicMock,
    mock_download: MagicMock,
) -> None:
    """Test run with available update."""
    mock_is_zipfile.return_value = True
    mock_local = MagicMock(version="1.0.0")
    mock_remote = MagicMock(
        version="2.0.0",
        release_url="https://example.com/release",
        hash="abc",
        algo="sha256",
    )
    mock_check.return_value = (True, mock_local, mock_remote)
    mock_download.return_value = "/path/to/downloaded"

    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 0
    mock_download.assert_called_once()


@patch("cosmofy.self.update.check")
@patch("cosmofy.self.update.zipfile.ZipFile")
@patch("cosmofy.self.update.is_zipfile")
def test_run_update_error(
    mock_is_zipfile: MagicMock,
    mock_zipfile: MagicMock,
    mock_check: MagicMock,
) -> None:
    """Test run handles update errors."""
    mock_is_zipfile.return_value = True
    mock_check.side_effect = RuntimeError("Update failed")

    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 2


@patch("cosmofy.self.update.download_release")
@patch("cosmofy.self.update.check")
@patch("cosmofy.self.update.zipfile.ZipFile")
@patch("cosmofy.self.update.is_zipfile")
def test_run_json_output(
    mock_is_zipfile: MagicMock,
    mock_zipfile: MagicMock,
    mock_check: MagicMock,
    mock_download: MagicMock,
    capsys: MagicMock,
) -> None:
    """Test run with JSON output format."""
    mock_is_zipfile.return_value = True
    mock_local = MagicMock(version="1.0.0")
    mock_remote = MagicMock(version="2.0.0", release_url="", hash="", algo="")
    mock_check.return_value = (True, mock_local, mock_remote)

    args = baton.parse(Args, split("--output-format json"))
    result = run(args)
    assert result == 0

    captured = capsys.readouterr()
    assert '"update_available": true' in captured.out
    assert '"local_version": "1.0.0"' in captured.out
    assert '"remote_version": "2.0.0"' in captured.out
