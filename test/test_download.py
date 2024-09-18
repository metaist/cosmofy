"""Test download functions."""

# std
from datetime import datetime
from datetime import timezone
from http.client import HTTPMessage
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch
from urllib.error import HTTPError
import hashlib

# pkg
from cosmofy import downloader


@patch("cosmofy.downloader.urlopen")
@patch("cosmofy.downloader.Path.open")
@patch("cosmofy.downloader.Path.mkdir")
def test_download(_mkdir: MagicMock, _open: MagicMock, _urlopen: MagicMock) -> None:
    """Download url."""
    # read url
    _response = MagicMock()
    _response.read.side_effect = [b"chunk1", b"chunk2", b""]
    _urlopen.return_value.__enter__.return_value = _response

    # open file
    _output = MagicMock()
    _open.return_value.__enter__.return_value = _output

    # test
    url = "http://example.com"
    path = Path("fake")
    result = downloader.download(url, path)

    _urlopen.assert_called_once_with(url)
    _mkdir.assert_called_once_with(parents=True, exist_ok=True)
    _output.write.assert_any_call(b"chunk1")
    _output.write.assert_any_call(b"chunk2")
    assert result == path


@patch("cosmofy.downloader.Path.exists")
@patch("cosmofy.downloader.download")
def test_download_if_not_exists(_download: MagicMock, _exists: MagicMock) -> None:
    """Call download when there's no file."""
    # local
    _exists.return_value = False  # file does not exist

    # test
    url = "http://example.com"
    path = Path("fake")
    downloader.download_if_newer(url, path)

    _download.assert_called()


@patch("cosmofy.downloader.Path.exists")
@patch("cosmofy.downloader.Path.stat")
@patch("cosmofy.downloader.urlopen")
@patch("cosmofy.downloader.parsedate_to_datetime")
@patch("cosmofy.downloader.download")
def test_download_if_newer(
    _download: MagicMock,
    _parsedate: MagicMock,
    _urlopen: MagicMock,
    _stat: MagicMock,
    _exists: MagicMock,
) -> None:
    """Call download if there's a newer version."""
    # local
    _exists.return_value = True  # File exists
    _stat.return_value.st_mtime = datetime(2023, 9, 1, tzinfo=timezone.utc).timestamp()
    _stat.return_value.st_mode = 33204  # for Path.open

    # remote
    _response = MagicMock()
    _response.headers.get.return_value = "Wed, 02 Sep 2023 00:00:00 GMT"
    _response.read.side_effect = [b"chunk1", b"chunk2", b""]
    _urlopen.return_value.__enter__.return_value = _response
    _parsedate.return_value = datetime(2023, 9, 2, tzinfo=timezone.utc)

    # test
    url = "http://example.com"
    path = Path("fake")
    downloader.download_if_newer(url, path)

    assert _urlopen.called
    assert _download.called


@patch("cosmofy.downloader.Path.exists")
@patch("cosmofy.downloader.Path.stat")
@patch("cosmofy.downloader.urlopen")
@patch("cosmofy.downloader.parsedate_to_datetime")
@patch("cosmofy.downloader.download")
def test_download_if_not_newer(
    _download: MagicMock,
    _parsedate: MagicMock,
    _urlopen: MagicMock,
    _stat: MagicMock,
    _exists: MagicMock,
) -> None:
    # local
    _exists.return_value = True  # File exists
    _stat.return_value.st_mtime = datetime(2023, 9, 2, tzinfo=timezone.utc).timestamp()

    # remote
    _response = MagicMock()
    _response.headers.get.return_value = "Wed, 01 Sep 2023 00:00:00 GMT"
    _urlopen.return_value.__enter__.return_value = _response
    _parsedate.return_value = datetime(2023, 9, 1, tzinfo=timezone.utc)

    # test
    url = "http://example.com"
    path = Path("path")
    result = downloader.download_if_newer(url, path)

    _urlopen.assert_called_once()
    _download.assert_not_called()
    assert result == path


@patch("cosmofy.downloader.urlopen")
@patch("cosmofy.downloader.Path.open", new_callable=mock_open)
@patch("cosmofy.downloader.Path.mkdir")
def test_download_and_hash(
    _mkdir: MagicMock, _open: MagicMock, _urlopen: MagicMock
) -> None:
    """Download and hash content."""
    _response = MagicMock()
    _response.read.side_effect = [b"chunk1", b""]
    _urlopen.return_value.__enter__.return_value = _response

    url = "https://example.com"
    path = Path("fake")
    result = downloader.download_and_hash(url, path)

    _mkdir.assert_called_once()
    _open().write.assert_any_call(b"chunk1")
    assert result == hashlib.sha256(b"chunk1").hexdigest()


@patch("cosmofy.downloader.download_and_hash")
@patch("cosmofy.downloader.move_executable")
@patch("cosmofy.downloader.tempfile.NamedTemporaryFile", new_callable=mock_open)
def test_download_release(
    _temp: MagicMock, _move: MagicMock, _download: MagicMock
) -> None:
    """Download binary."""
    _temp.name = "/tmp/temp"

    url = "https://example.com/fake"
    path = Path("fake")
    expected = "abcdef"

    # normal
    _download.return_value = expected
    _move.return_value = path
    result = downloader.download_release(url, path, expected)
    assert result == path

    # bad hash
    _download.return_value = "unexpected"
    result = downloader.download_release(url, path, expected)
    assert result is None

    # not found => hint
    _download.side_effect = HTTPError(
        "https://example/fake", 404, "Not Found", HTTPMessage(), None
    )
    result = downloader.download_release(url, path, expected)
    assert result is None

    # no hint
    _download.side_effect = HTTPError(
        "https://example/fake", 500, "Server Error", HTTPMessage(), None
    )
    result = downloader.download_release(url, path, expected)
    assert result is None


@patch("cosmofy.downloader.Receipt.from_url")
def test_download_receipt(_from_url: MagicMock) -> None:
    """Download a receipt."""
    expected = downloader.Receipt()
    _from_url.return_value = expected

    url = "https://example.com/fake.json"
    assert downloader.download_receipt(url) == expected

    # not found => hint
    _from_url.side_effect = HTTPError(url, 404, "Not Found", HTTPMessage(), None)
    assert downloader.download_receipt(url) is None

    # no hint
    _from_url.side_effect = HTTPError(url, 500, "Server Error", HTTPMessage(), None)
    assert downloader.download_receipt(url) is None
