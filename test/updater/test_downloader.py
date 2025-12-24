# lib
import pytest

# pkg
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
