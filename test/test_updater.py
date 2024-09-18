"""Updater."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch
from datetime import datetime
from datetime import timezone

# pkg
from cosmofy import updater


@patch("cosmofy.updater.zipfile.ZipFile")
@patch("cosmofy.updater.Receipt.from_dict")
@patch("cosmofy.updater.download_receipt")
@patch("cosmofy.updater.download_release")
def test_updater(
    _release: MagicMock, _receipt: MagicMock, _from_dict: MagicMock, _ZipFile: MagicMock
) -> None:
    """Self-updater."""
    path = Path("/tmp/fake")
    _ZipFile.return_value.__enter__.return_value.read.return_value = "{}"
    _from_dict.return_value = updater.Receipt(
        date=datetime(2000, 1, 1, tzinfo=timezone.utc),
        receipt_url="https://example.com/fake.json",
    )
    _receipt.return_value = updater.Receipt(
        kind="published",
        date=datetime(2000, 1, 1, tzinfo=timezone.utc),
        receipt_url="https://example.com/fake.json",
    )

    # nothing new
    assert updater.self_update(path) == 0

    # newer
    _receipt.return_value = updater.Receipt(
        kind="published", date=datetime(2000, 1, 2, tzinfo=timezone.utc)
    )
    _release.return_value = path
    assert updater.self_update(path) == 0

    # error getting receipt
    _receipt.return_value = None
    assert updater.self_update(path) == 1

    # error getting release
    _receipt.return_value = updater.Receipt(
        kind="published", date=datetime(2000, 1, 2, tzinfo=timezone.utc)
    )
    _release.return_value = None
    assert updater.self_update(path) == 1


@patch("cosmofy.updater.self_update")
@patch("cosmofy.updater.run_python")
def test_main(_run_python: MagicMock, _self_update: MagicMock) -> None:
    """Main entry point."""
    _self_update.return_value = 0
    _run_python.return_value = 0

    assert updater.main([]) == 0
    _run_python.assert_called_with([])

    assert updater.main(split("--self-update")) == 0
    _self_update.assert_called()

    assert updater.main(split("--self-update --help")) == 0
    assert updater.main(split("-h --self-update")) == 0
    assert updater.main(split("--self-update --version")) == 0
    assert updater.main(split("--self-update --debug")) == 0
