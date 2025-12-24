#!/usr/bin/env python
"""Cosmofy self-updater."""

# std
from __future__ import annotations
from os import environ as ENV
from pathlib import Path
import logging
import sys
import zipfile

# pkg
from cosmofy import __pubdate__
from cosmofy import __version__

from .add import RECEIPT_URL
from .add import RELEASE_URL
from .check import check
from .downloader import cleanup_old_executable
from .downloader import download_release
from .pythonoid import run_python

log_normal = "%(levelname)s: %(message)s"
log_debug = "%(name)s.%(funcName)s: %(levelname)s: %(message)s"
log = logging.getLogger(__name__)


usage = f"""\
This program is bundled into Cosmopolitan Python apps
to give them the ability to update themselves.
See: https://github.com/metaist/cosmofy

Usage: <bundle> --self-update [--help] [--version] [--debug]

Options:
  --self-update     Run this updater instead of <bundle>
  -h, --help        Show this message and exit.
  --version         Show updater version and exit.
  --debug           Show debug messages.

  [env: RECEIPT_URL={RECEIPT_URL}]
  Override the embedded URL for downloading update metadata.

  [env: RELEASE_URL={RELEASE_URL}]
  Override the published URL for downloading the update.
"""


def self_update(path: Path) -> int:
    """Run the self-updater."""
    with zipfile.ZipFile(path, "r") as bundle:
        is_newer, local, remote = check(bundle, receipt_url=RECEIPT_URL, dry_run=False)
        if not is_newer:
            return 0

    url = ENV.get("RELEASE_URL", remote.release_url)
    dest = download_release(url, path, remote.hash, remote.algo)
    if not dest:
        return 1

    log.info(f"Updated to {remote.version}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for self-updater."""
    cleanup_old_executable(Path(sys.executable))

    args = argv or sys.argv[1:]
    if "--self-update" in args:
        if "-h" in args or "--help" in args:
            print(usage, end="")
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
