#!/usr/bin/env python
"""Cosmofy self-updater."""

# std
from __future__ import annotations
from os import environ as ENV
from pathlib import Path
from typing import List
from typing import Optional
import json
import logging
import sys
import zipfile

# pkg
from .downloader import download_receipt
from .downloader import download_release
from .pythonoid import run_python
from .receipt import Receipt

__version__ = "0.1.0"
__pubdate__ = "unpublished"

log_normal = "%(levelname)s: %(message)s"
log_debug = "%(name)s.%(funcName)s: %(levelname)s: %(message)s"
log = logging.getLogger(__name__)


PATH_COSMOFY = "Lib/site-packages/cosmofy"
"""Path within zip file to cosmofy package."""

PATH_RECEIPT = f"{PATH_COSMOFY}/.cosmofy.json"
"""Path within the zip file to the local receipt."""

USAGE = f"""\
This program is bundled into Cosmopolitan Python apps
to give them the ability to update themselves.
See: https://github.com/metaist/cosmofy

Usage: {Path(sys.executable).name} --self-update [--help] [--version] [--debug]

Options:
  --self-update
    Indicates that this self-updater should run instead of the usual
    program.

  -h, --help
   Show this message and exit.

  --debug
    Show debug messages.

Environment:
  RECEIPT_URL={ENV.get("RECEIPT_URL")}
    If set, this URL will override the built-in URL for downloading
    update metadata.

  RELEASE_URL={ENV.get("RELEASE_URL")}
    If set, this URL will override the published URL for downloading
    the update.
"""


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
            print(USAGE, end="")
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
