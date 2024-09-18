"""Test download functions."""

# std
from datetime import datetime
from datetime import timezone
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch
from urllib.error import HTTPError
from http.client import HTTPMessage
import hashlib

# pkg
from cosmofy import updater


@patch("cosmofy.updater.urlopen")
@patch("cosmofy.updater.Path.open")
@patch("cosmofy.updater.Path.mkdir")
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
    result = updater.download(url, path)

    _urlopen.assert_called_once_with(url)
    _mkdir.assert_called_once_with(parents=True, exist_ok=True)
    _output.write.assert_any_call(b"chunk1")
    _output.write.assert_any_call(b"chunk2")
    assert result == path


@patch("cosmofy.updater.Path.exists")
@patch("cosmofy.updater.download")
def test_download_if_not_exists(_download: MagicMock, _exists: MagicMock) -> None:
    """Call download when there's no file."""
    # local
    _exists.return_value = False  # file does not exist

    # test
    url = "http://example.com"
    path = Path("fake")
    updater.download_if_newer(url, path)

    _download.assert_called()


@patch("cosmofy.updater.Path.exists")
@patch("cosmofy.updater.Path.stat")
@patch("cosmofy.updater.urlopen")
@patch("cosmofy.updater.parsedate_to_datetime")
@patch("cosmofy.updater.download")
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
    updater.download_if_newer(url, path)

    assert _urlopen.called
    assert _download.called


@patch("cosmofy.updater.Path.exists")
@patch("cosmofy.updater.Path.stat")
@patch("cosmofy.updater.urlopen")
@patch("cosmofy.updater.parsedate_to_datetime")
@patch("cosmofy.updater.download")
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
    result = updater.download_if_newer(url, path)

    _urlopen.assert_called_once()
    _download.assert_not_called()
    assert result == path


@patch("cosmofy.updater.urlopen")
@patch("cosmofy.updater.Path.open", new_callable=mock_open)
@patch("cosmofy.updater.Path.mkdir")
def test_download_and_hash(
    _mkdir: MagicMock, _open: MagicMock, _urlopen: MagicMock
) -> None:
    """Download and hash content."""
    _response = MagicMock()
    _response.read.side_effect = [b"chunk1", b""]
    _urlopen.return_value.__enter__.return_value = _response

    url = "https://example.com"
    path = Path("fake")
    result = updater.download_and_hash(url, path)

    _mkdir.assert_called_once()
    _open().write.assert_any_call(b"chunk1")
    assert result == hashlib.sha256(b"chunk1").hexdigest()


@patch("cosmofy.updater.download_and_hash")
@patch("cosmofy.updater.move_executable")
@patch("cosmofy.updater.tempfile.NamedTemporaryFile", new_callable=mock_open)
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
    result = updater.download_release(url, path, expected)
    assert result == path

    # bad hash
    _download.return_value = "unexpected"
    result = updater.download_release(url, path, expected)
    assert result is None

    # not found => hint
    _download.side_effect = HTTPError(
        "https://example/fake", 404, "Not Found", HTTPMessage(), None
    )
    result = updater.download_release(url, path, expected)
    assert result is None

    # no hint
    _download.side_effect = HTTPError(
        "https://example/fake", 500, "Server Error", HTTPMessage(), None
    )
    result = updater.download_release(url, path, expected)
    assert result is None


@patch("cosmofy.updater.Receipt.from_url")
def test_download_receipt(_from_url: MagicMock) -> None:
    """Download a receipt."""
    expected = updater.Receipt()
    _from_url.return_value = expected

    url = "https://example.com/fake.json"
    assert updater.download_receipt(url) == expected

    # not found => hint
    _from_url.side_effect = HTTPError(url, 404, "Not Found", HTTPMessage(), None)
    assert updater.download_receipt(url) is None

    # no hint
    _from_url.side_effect = HTTPError(url, 500, "Server Error", HTTPMessage(), None)
    assert updater.download_receipt(url) is None
