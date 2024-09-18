#!/usr/bin/env python
"""Cosmofy self-updater.

This program is bundled into Cosmopolitan Python apps
to give them the ability to update themselves.
See: https://github.com/metaist/cosmofy

Usage: {program} --self-update [--help] [--version] [--debug]

Options:

  --self-update
    Indicates that this self-updater should run instead of the usual
    program.

  -h, --help
   Show this message and exit.

  --debug
    Show debug messages.

Environment:

  RECEIPT_URL={RECEIPT_URL}
    If set, this URL will override the built-in URL for downloading
    update metadata.

  RELEASE_URL={RELEASE_URL}
    If set, this URL will override the published URL for downloading
    the update.
"""

# std
from __future__ import annotations
from datetime import datetime
from datetime import timezone
from email.utils import parsedate_to_datetime
from os import environ as ENV
from pathlib import Path
from typing import List
from typing import Optional
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen
import hashlib
import json
import logging
import shutil
import stat
import sys
import tempfile
import zipfile

# pkg
from .pythonoid import run_python
from .receipt import DEFAULT_HASH
from .receipt import Receipt

__version__ = "0.1.0"
__pubdate__ = "unpublished"

log_normal = "%(levelname)s: %(message)s"
log_debug = "%(name)s.%(funcName)s: %(levelname)s: %(message)s"
log = logging.getLogger(__name__)


PATH_RECEIPT = "Lib/site-packages/cosmofy/.cosmofy.json"
"""Path within the zip file to the local receipt."""

CHUNK_SIZE = 65536
"""Default chunk size."""


def move_executable(src: Path, dest: Path) -> Path:
    """Set the executable bit and move a file."""
    mode = src.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    src.chmod(mode)

    dest.parent.mkdir(parents=True, exist_ok=True)
    # TODO 2024-10-31 @ py3.8 EOL: use `Path` instead of `str`
    shutil.move(str(src), str(dest))
    return dest


def download(url: str, path: Path) -> Path:
    """Download `url` to path."""
    log.info(f"Downloading {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, path.open("wb") as output:
        while chunk := response.read(CHUNK_SIZE):
            output.write(chunk)
    return path


def download_if_newer(url: str, path: Path) -> Path:
    """Download `url` to `path` if `url` is newer."""
    exists = path.exists()
    need_download = not exists  # guess: exists => already downloaded
    if exists:
        local = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        response = urlopen(Request(url, method="HEAD"))
        remote = parsedate_to_datetime(response.headers.get("Last-Modified"))
        need_download = remote > local  # only download if newer
    return download(url, path) if need_download else path


def download_and_hash(url: str, path: Path, algo: str = DEFAULT_HASH) -> str:
    """Download `url` to `path` and return the hash."""
    log.info(f"Downloading {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.new(algo)
    with urlopen(url) as response, path.open("wb") as output:
        while chunk := response.read(CHUNK_SIZE):
            print(chunk)
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def download_release(
    url: str, path: Path, expected: str, algo: str = DEFAULT_HASH
) -> Optional[Path]:
    """Download release from `url` checking the hash along the way."""
    with tempfile.NamedTemporaryFile(delete=False) as out:
        temp = Path(out.name)
        try:
            log.info(f"Download: {url}")
            received = download_and_hash(url, temp, algo)
        except HTTPError as e:
            log.error(f"{e}: {url}")
            if e.code in [401, 404]:
                log.info("Hint: Set `RELEASE_URL` environment variable to override.")
            return None

        if received != expected:
            log.error(f"Hash mismatch: expected={expected}, received={received}")
            temp.unlink(missing_ok=True)
            return None

    log.debug(f"Overwriting: {path}")
    return move_executable(temp, path)


def download_receipt(url: str) -> Optional[Receipt]:
    """Try to download a receipt."""
    receipt = None
    try:
        log.info(f"Download: {url}")
        receipt = Receipt.from_url(url)
    except HTTPError as e:
        log.error(f"{e}: {url}")
        if e.code in [401, 404]:
            log.info("Hint: Set `RECEIPT_URL` environment variable to override.")
    return receipt


def self_update(path: Path) -> int:
    """Run the self-updater."""
    with zipfile.ZipFile(path, "r") as f:
        local = Receipt.from_dict(json.loads(f.read(PATH_RECEIPT)))
        log.debug(f"Embedded receipt: {local}")

    url = ENV.get("RECEIPT_URL", local.receipt_url)
    log.debug(f"Receipt URL: {url}")

    remote = download_receipt(url)
    log.debug(f"Published receipt: {remote}")
    if not remote:
        return 1

    if not remote.is_newer(local):
        log.info("No updates found.")
        return 0
    log.info(f"New version found: {remote.version} ({remote.date})")

    url = ENV.get("RELEASE_URL", remote.release_url)
    dest = download_release(url, path, remote.hash, remote.algo)
    if not dest:
        return 1

    log.info(f"Updated to {remote.version}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for self-updater."""
    args = argv or sys.argv[1:]
    if "--self-update" in args:
        if "-h" in args or "--help" in args:
            assert __doc__
            doc = __doc__.format(
                program=Path(sys.executable).name,
                RECEIPT_URL=ENV.get("RECEIPT_URL", ""),
                RELEASE_URL=ENV.get("RELEASE_URL", ""),
            )
            print(doc)
            return 0
        if "--version" in args:
            print(f"cosmofy.updater {__version__} ({__pubdate__})")
            return 0
        level = logging.DEBUG if "--debug" in args else logging.INFO
        logging.basicConfig(level=level, format=log_normal)
        return self_update(Path(sys.executable))
    return run_python(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
