"""Test updater check command."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.error import HTTPError
from zipfile import ZipFile
import json
import tempfile

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.updater.add import PATH_RECEIPT
from cosmofy.updater.check import Args
from cosmofy.updater.check import check
from cosmofy.updater.check import get_local_receipt
from cosmofy.updater.check import get_remote_receipt
from cosmofy.updater.check import run
from cosmofy.updater.receipt import Receipt
from cosmofy.updater.receipt import RECEIPT_SCHEMA
from cosmofy.zipfile2 import ZipFile2


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip"))
    assert args.bundle == Path("bundle.zip")
    assert args.receipt_url == ""


def test_arg_parsing_with_url() -> None:
    """Test Args parsing with receipt URL."""
    args = baton.parse(
        Args, split("bundle.zip --receipt-url https://example.com/r.json")
    )
    assert args.receipt_url == "https://example.com/r.json"


def test_get_local_receipt() -> None:
    """Test get_local_receipt extracts receipt from bundle."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        receipt_data = {
            "$schema": RECEIPT_SCHEMA,
            "kind": "embedded",
            "receipt_url": "https://example.com/receipt.json",
            "release_url": "https://example.com/file.exe",
            "version": "1.0.0",
            "date": "2024-01-01T00:00:00Z",
            "algo": "sha256",
            "hash": "abc123",
        }

        with ZipFile2(path, "w") as z:
            z.writestr(PATH_RECEIPT, json.dumps(receipt_data))

        with ZipFile(path, "r") as z:
            receipt = get_local_receipt(z)
            assert receipt.receipt_url == "https://example.com/receipt.json"
            assert receipt.release_url == "https://example.com/file.exe"
            assert receipt.version == "1.0.0"
    finally:
        path.unlink(missing_ok=True)


def test_get_local_receipt_not_found() -> None:
    """Test get_local_receipt raises when no receipt."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "content")

        with ZipFile(path, "r") as z:
            with pytest.raises(FileNotFoundError) as exc:
                get_local_receipt(z)
            assert "cannot find cosmofy receipt" in str(exc.value)
    finally:
        path.unlink(missing_ok=True)


@patch("cosmofy.updater.check.Receipt.from_url")
def test_get_remote_receipt(mock_from_url: MagicMock) -> None:
    """Test get_remote_receipt downloads receipt."""
    mock_receipt = Receipt(
        receipt_url="https://example.com/r.json",
        version="2.0.0",
    )
    mock_from_url.return_value = mock_receipt

    result = get_remote_receipt("https://example.com/r.json")
    assert result.version == "2.0.0"
    mock_from_url.assert_called_once_with("https://example.com/r.json")


def test_get_remote_receipt_dry_run() -> None:
    """Test get_remote_receipt in dry run returns empty receipt."""
    result = get_remote_receipt("https://example.com/r.json", dry_run=True)
    assert result.version == ""  # empty receipt


@patch("cosmofy.updater.check.Receipt.from_url")
def test_get_remote_receipt_http_error(mock_from_url: MagicMock) -> None:
    """Test get_remote_receipt handles HTTP errors."""
    mock_from_url.side_effect = HTTPError(
        "https://example.com/r.json",
        404,
        "Not Found",
        {},  # type: ignore[arg-type]
        None,
    )

    with pytest.raises(FileNotFoundError) as exc:
        get_remote_receipt("https://example.com/r.json")
    assert "cannot download published receipt" in str(exc.value)


@patch("cosmofy.updater.check.get_remote_receipt")
def test_check_newer_version(mock_remote: MagicMock) -> None:
    """Test check detects newer version."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        local_receipt = {
            "$schema": RECEIPT_SCHEMA,
            "kind": "embedded",
            "receipt_url": "https://example.com/r.json",
            "release_url": "https://example.com/file.exe",
            "version": "1.0.0",
            "date": "2024-01-01T00:00:00Z",
            "algo": "sha256",
            "hash": "abc123",
        }
        with ZipFile2(path, "w") as z:
            z.writestr(PATH_RECEIPT, json.dumps(local_receipt))

        mock_remote.return_value = Receipt(
            receipt_url="https://example.com/r.json",
            version="2.0.0",
            date="2024-06-01T00:00:00Z",
        )

        with ZipFile(path, "r") as z:
            is_newer, local, remote = check(z)
            assert is_newer is True
            assert local.version == "1.0.0"
            assert remote.version == "2.0.0"
    finally:
        path.unlink(missing_ok=True)


@patch("cosmofy.updater.check.get_remote_receipt")
def test_check_same_version(mock_remote: MagicMock) -> None:
    """Test check detects same version."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        local_receipt = {
            "$schema": RECEIPT_SCHEMA,
            "kind": "embedded",
            "receipt_url": "https://example.com/r.json",
            "release_url": "https://example.com/file.exe",
            "version": "1.0.0",
            "date": "2024-01-01T00:00:00Z",
            "algo": "sha256",
            "hash": "abc123",
        }
        with ZipFile2(path, "w") as z:
            z.writestr(PATH_RECEIPT, json.dumps(local_receipt))

        mock_remote.return_value = Receipt(
            receipt_url="https://example.com/r.json",
            version="1.0.0",
            date="2024-01-01T00:00:00Z",
        )

        with ZipFile(path, "r") as z:
            is_newer, local, remote = check(z)
            assert is_newer is False
    finally:
        path.unlink(missing_ok=True)


@patch("cosmofy.updater.check.check")
def test_run_success(mock_check: MagicMock, tmp_path: Path) -> None:
    """Test run command success."""
    mock_check.return_value = (False, Receipt(), Receipt())

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(Args, split(f"{bundle_path}"))
    result = run(args)
    assert result == 0


def test_run_no_bundle() -> None:
    """Test run command with nonexistent bundle returns error."""
    args = baton.parse(Args, split("nonexistent.zip"))
    result = run(args)
    assert result == 2
