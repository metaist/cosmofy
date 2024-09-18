"""Test Receipt."""

# std
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch
import json

# lib
import pytest

# pkg
from cosmofy.receipt import Receipt
from cosmofy.receipt import RECEIPT_SCHEMA


def test_is_newer() -> None:
    """Compare receipts."""
    r1 = Receipt(date="2000-01-01T00:00:00Z")
    r2 = Receipt(date="2000-01-02T00:00:00Z")
    assert r2.is_newer(r1)
    assert not r1.is_newer(r2)
    assert not r1.is_newer(r1)


def test_serialization() -> None:
    """Receipt serialization."""
    r1 = Receipt(date="2000-01-01T00:00:00Z")
    expected = {
        "$schema": RECEIPT_SCHEMA,
        "kind": "embedded",
        "date": "2000-01-01T00:00:00Z",
        "algo": "sha256",
        "hash": "",
        "receipt_url": "",
        "release_url": "",
        "version": "",
    }
    assert r1.asdict() == expected
    assert str(r1) == json.dumps(expected)


def test_validation() -> None:
    """Receipt validation."""
    assert Receipt.find_issues({}) == {
        "missing": [
            "$schema",
            "kind",
            "date",
            "algo",
            "hash",
            "receipt_url",
            "release_url",
            "version",
        ],
        "unknown": [],
        "malformed": [],
    }

    r1 = Receipt(date="2000-01-01T00:00:00Z")
    assert not r1.is_valid()
    assert Receipt.find_issues(r1.asdict()) == {
        "missing": [],
        "unknown": [],
        "malformed": ["receipt_url", "release_url"],
    }

    r1.receipt_url = "https://example.com/foo.json"
    r1.release_url = "https://example.com/foo"
    assert r1.is_valid()

    data = r1.asdict()
    data["foo"] = "bar"
    assert Receipt.find_issues(data) == {
        "missing": [],
        "unknown": ["foo"],
        "malformed": [],
    }


def test_update() -> None:
    """Update fields."""
    r1 = Receipt(date="2000-01-01T00:00:00Z")
    r2 = Receipt(date="2000-01-02T00:00:00Z")
    r2.update_from(r1, "date")
    assert r1 == r2

    r2.update(algo="sha1", date="2000-01-03T00:00:00Z")
    assert r2.algo == "sha1"
    assert r2.date == "2000-01-03T00:00:00Z"


def test_from_dict() -> None:
    """Receipt from dict."""
    data = {
        "$schema": RECEIPT_SCHEMA,
        "kind": "embedded",
        "date": "2000-01-01T00:00:00Z",
        "algo": "sha256",
        "hash": "",
        "receipt_url": "https://example.com/foo.json",
        "release_url": "https://example.com/foo",
        "version": "",
    }
    assert Receipt.from_dict(data)

    data["kind"] = "published"
    with pytest.raises(ValueError):
        Receipt.from_dict(data)


@patch("cosmofy.receipt.json.load")
@patch("cosmofy.receipt.urlopen")
def test_from_url(_urlopen: MagicMock, _load: MagicMock) -> None:
    """Receipt from url."""
    _urlopen.return_value.read.return_value = b"{}"
    _load.return_value = {}
    with pytest.raises(ValueError):
        Receipt.from_url("https://example.com/foo.json")


@patch("cosmofy.receipt.hashlib.new")
@patch("cosmofy.receipt.Path.read_bytes")
@patch("cosmofy.receipt.subprocess.run")
def test_from_path(_run: MagicMock, _read_bytes: MagicMock, _new: MagicMock) -> None:
    """Receipt with hash and version."""
    fake_hash = "0123456789abcdef"
    fake_ver = b"0.1.2"
    _new.return_value.hexdigest.return_value = fake_hash
    _read_bytes.return_value = b"fake content"
    _run.return_value.stdout = fake_ver
    assert Receipt.from_path(Path("fake")) == Receipt(hash=fake_hash, version="0.1.2")
    assert Receipt.from_path(Path("fake"), version="1.2.3") == Receipt(
        hash=fake_hash, version="1.2.3"
    )

    _run.return_value.stdout = b"no version information"
    assert Receipt.from_path(Path("fake")) == Receipt(hash=fake_hash, version="")
