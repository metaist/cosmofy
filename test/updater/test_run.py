"""Updater."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch

# pkg
from cosmofy.updater import run
from cosmofy.updater.receipt import Receipt


@patch("cosmofy.updater.run.zipfile.ZipFile")
@patch("cosmofy.updater.run.check")
@patch("cosmofy.updater.run.download_release")
def test_updater(
    _release: MagicMock,
    _check: MagicMock,
    _ZipFile: MagicMock,
) -> None:
    """Self-updater."""
    path = Path("/tmp/fake")
    _ZipFile.return_value.__enter__.return_value.read.return_value = "{}"

    local = Receipt(
        date="2000-01-01T00:00:00Z",
        receipt_url="https://example.com/fake.json",
    )
    remote = Receipt(
        kind="published",
        date="2000-01-01T00:00:00Z",
        receipt_url="https://example.com/fake.json",
    )
    _check.return_value = (False, local, remote)

    # nothing new
    assert run.self_update(path) == 0

    # newer
    _check.return_value = (
        True,
        local,
        Receipt(kind="published", date="2000-01-02T00:00:00Z"),
    )
    _release.return_value = path
    assert run.self_update(path) == 0

    # error getting release
    _release.return_value = None
    assert run.self_update(path) == 1


@patch("cosmofy.updater.run.self_update")
@patch("cosmofy.updater.run.run_python")
def test_main(_run_python: MagicMock, _self_update: MagicMock) -> None:
    """Main entry point."""
    _self_update.return_value = 0
    _run_python.return_value = 0

    assert run.main([]) == 0
    _run_python.assert_called_with([])

    assert run.main(split("--self-update")) == 0
    _self_update.assert_called()

    assert run.main(split("--self-update --help")) == 0
    assert run.main(split("-h --self-update")) == 0
    assert run.main(split("--self-update --version")) == 0
    assert run.main(split("--self-update --debug")) == 0
