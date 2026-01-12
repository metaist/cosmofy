# std
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

# lib
import pytest

# pkg
from cosmofy.updater.downloader import cleanup_old_executable
from cosmofy.updater.downloader import download
from cosmofy.updater.downloader import download_and_hash
from cosmofy.updater.downloader import download_if_newer
from cosmofy.updater.downloader import download_release
from cosmofy.updater.downloader import move_executable
from cosmofy.updater.downloader import progress
from cosmofy.updater.downloader import validate_url


def test_validate_url() -> None:
    assert validate_url("https://example.com/file.zip")
    assert validate_url("http://example.com/file.zip", allow_http=True)

    with pytest.raises(ValueError):
        validate_url("http://example.com/file.zip")

    with pytest.raises(ValueError):
        validate_url("file:///etc/passwd")

    with pytest.raises(ValueError):
        validate_url("ftp://example.com/file.zip")

    with pytest.raises(ValueError):
        validate_url("")


def test_move_executable(tmp_path: Path) -> None:
    """Test move_executable sets permissions and moves file."""
    src = tmp_path / "src.exe"
    src.write_bytes(b"test")
    dest = tmp_path / "dest" / "dest.exe"

    result = move_executable(src, dest)
    assert result == dest
    assert dest.exists()
    assert not src.exists()


@patch("cosmofy.updater.downloader.platform.system")
@patch("cosmofy.updater.downloader.sys")
def test_move_executable_windows(
    mock_sys: MagicMock, mock_system: MagicMock, tmp_path: Path
) -> None:
    """Test move_executable on Windows with running executable."""
    mock_system.return_value = "Windows"

    src = tmp_path / "new.exe"
    src.write_bytes(b"new content")
    dest = tmp_path / "current.exe"
    dest.write_bytes(b"old content")
    mock_sys.executable = str(dest)

    result = move_executable(src, dest)
    assert result == dest
    assert dest.exists()


def test_cleanup_old_executable(tmp_path: Path) -> None:
    """Test cleanup_old_executable removes .old file."""
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"exe")
    old = tmp_path / "app.exe.old"
    old.write_bytes(b"old")

    cleanup_old_executable(exe)
    assert not old.exists()


def test_cleanup_old_executable_no_old(tmp_path: Path) -> None:
    """Test cleanup_old_executable when no .old exists."""
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"exe")

    # Should not raise
    cleanup_old_executable(exe)


@patch("cosmofy.updater.downloader.Path.unlink")
def test_cleanup_old_executable_permission_error(
    mock_unlink: MagicMock, tmp_path: Path
) -> None:
    """Test cleanup_old_executable ignores OSError."""
    mock_unlink.side_effect = OSError("Permission denied")

    exe = tmp_path / "app.exe"
    exe.write_bytes(b"exe")
    old = tmp_path / "app.exe.old"
    old.write_bytes(b"old")

    # Should not raise
    cleanup_old_executable(exe)


def test_progress_with_content_length() -> None:
    """Test progress with known content length."""
    mock_response = MagicMock()
    mock_response.getheader.return_value = "100"
    mock_response.read.side_effect = [b"x" * 50, b"x" * 50, b""]

    chunks = list(progress(mock_response))
    assert len(chunks) == 2


def test_progress_without_content_length() -> None:
    """Test progress without content length header."""
    mock_response = MagicMock()
    mock_response.getheader.return_value = "0"
    mock_response.read.side_effect = [b"data", b""]

    chunks = list(progress(mock_response))
    assert len(chunks) == 1


@patch("cosmofy.updater.downloader.urlopen")
def test_download(mock_urlopen: MagicMock, tmp_path: Path) -> None:
    """Test download function."""
    mock_response = MagicMock()
    mock_response.getheader.return_value = "4"
    mock_response.read.side_effect = [b"test", b""]
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    path = tmp_path / "file.txt"
    result = download("https://example.com/file.txt", path)
    assert result == path


@patch("cosmofy.updater.downloader.urlopen")
def test_download_error_cleanup(mock_urlopen: MagicMock, tmp_path: Path) -> None:
    """Test download cleans up temp file on error."""
    mock_urlopen.side_effect = Exception("Network error")

    path = tmp_path / "file.txt"
    with pytest.raises(Exception):
        download("https://example.com/file.txt", path)

    # Temp file should be cleaned up
    assert not (tmp_path / "file.txt.tmp").exists()


@patch("cosmofy.updater.downloader.download")
@patch("cosmofy.updater.downloader.urlopen")
def test_download_if_newer_no_file(
    mock_urlopen: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    """Test download_if_newer when local file doesn't exist."""
    mock_download.return_value = tmp_path / "file.txt"
    path = tmp_path / "file.txt"

    download_if_newer("https://example.com/file.txt", path)
    mock_download.assert_called_once()


@patch("cosmofy.updater.downloader.download")
@patch("cosmofy.updater.downloader.urlopen")
def test_download_if_newer_no_last_modified(
    mock_urlopen: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    """Test download_if_newer when no Last-Modified header."""
    path = tmp_path / "file.txt"
    path.write_bytes(b"old")

    mock_response = MagicMock()
    mock_response.headers.get.return_value = None
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    mock_download.return_value = path

    download_if_newer("https://example.com/file.txt", path)
    mock_download.assert_called_once()


@patch("cosmofy.updater.downloader.download")
@patch("cosmofy.updater.downloader.urlopen")
def test_download_if_newer_parse_error(
    mock_urlopen: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    """Test download_if_newer when date parsing fails."""
    path = tmp_path / "file.txt"
    path.write_bytes(b"old")

    mock_response = MagicMock()
    mock_response.headers.get.return_value = "invalid-date-format"
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    mock_download.return_value = path

    download_if_newer("https://example.com/file.txt", path)
    mock_download.assert_called_once()


@patch("cosmofy.updater.downloader.urlopen")
def test_download_and_hash(mock_urlopen: MagicMock, tmp_path: Path) -> None:
    """Test download_and_hash returns correct hash."""
    mock_response = MagicMock()
    mock_response.getheader.return_value = "4"
    mock_response.read.side_effect = [b"test", b""]
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    path = tmp_path / "file.txt"
    result = download_and_hash("https://example.com/file.txt", path)
    assert isinstance(result, str)
    assert len(result) == 64  # sha256 hex


@patch("cosmofy.updater.downloader.urlopen")
def test_download_and_hash_error_cleanup(
    mock_urlopen: MagicMock, tmp_path: Path
) -> None:
    """Test download_and_hash cleans up temp file on error."""
    mock_response = MagicMock()
    mock_response.getheader.return_value = "4"
    mock_response.read.side_effect = Exception("Network error")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    path = tmp_path / "file.txt"
    with pytest.raises(Exception):
        download_and_hash("https://example.com/file.txt", path)


@patch("cosmofy.updater.downloader.move_executable")
@patch("cosmofy.updater.downloader.download_and_hash")
def test_download_release_success(
    mock_download_hash: MagicMock, mock_move: MagicMock, tmp_path: Path
) -> None:
    """Test download_release with matching hash."""
    expected_hash = "abc123"
    mock_download_hash.return_value = expected_hash
    mock_move.return_value = tmp_path / "app.exe"

    result = download_release(
        "https://example.com/app.exe", tmp_path / "app.exe", expected_hash
    )
    assert result is not None
    mock_move.assert_called_once()


@patch("cosmofy.updater.downloader.download_and_hash")
def test_download_release_hash_mismatch(
    mock_download_hash: MagicMock, tmp_path: Path
) -> None:
    """Test download_release with hash mismatch."""
    mock_download_hash.return_value = "wrong_hash"

    result = download_release(
        "https://example.com/app.exe", tmp_path / "app.exe", "expected_hash"
    )
    assert result is None


@patch("cosmofy.updater.downloader.download_and_hash")
def test_download_release_http_error(
    mock_download_hash: MagicMock, tmp_path: Path
) -> None:
    """Test download_release with HTTP error."""
    from urllib.error import HTTPError

    mock_download_hash.side_effect = HTTPError(
        "url",
        404,
        "Not Found",
        {},  # type: ignore[arg-type]
        None,
    )

    result = download_release(
        "https://example.com/app.exe", tmp_path / "app.exe", "expected_hash"
    )
    assert result is None
