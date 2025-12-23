#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from urllib.error import HTTPError
from zipfile import ZipFile
import json
import logging
import sys

# pkg
from cosmofy.args import common_args
from cosmofy.args import CommonArgs
from cosmofy.args import get_banner
from cosmofy.args import global_options
from cosmofy.baton import arg
from cosmofy.baton import Command

from .add import PATH_RECEIPT
from .add import RECEIPT_URL
from .receipt import Receipt


log = logging.getLogger(__name__)


usage = f"""\
EXPERIMENTAL: Check if a cosmofy bundle has an update.

Usage: cosmofy updater check <BUNDLE> [OPTIONS]

Arguments:
{common_args}

Options:
      --receipt-url <URL>   override the published receipt URL
                            [env: RECEIPT_URL={RECEIPT_URL}]

{global_options}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage
    receipt_url: str = arg(RECEIPT_URL)


def get_local_receipt(bundle: ZipFile) -> Receipt:
    """Return `Receipt` embedded in `bundle`."""
    if PATH_RECEIPT not in bundle.NameToInfo:
        raise FileNotFoundError("cannot find cosmofy receipt in bundle")
    return Receipt.from_dict(json.loads(bundle.read(PATH_RECEIPT)))


def get_remote_receipt(url: str, *, dry_run: bool = False) -> Receipt:
    """Try to download a receipt."""
    banner = get_banner(dry_run)
    log.info(f"{banner}download: {url}")
    try:
        if dry_run:
            return Receipt()
        else:
            return Receipt.from_url(url)
    except HTTPError as e:
        log.error(f"{e}: {url}")
        raise FileNotFoundError("cannot download published receipt") from e


def check(
    bundle: ZipFile, *, receipt_url: str = "", dry_run: bool = False
) -> tuple[bool, Receipt, Receipt]:
    """Return published receipt after checking if there are is a newer version."""
    banner = get_banner(dry_run)
    local = get_local_receipt(bundle)
    log.debug(f"{banner}embedded receipt: {local}")

    url = receipt_url or local.receipt_url
    log.debug(f"{banner}receipt URL: {url}")

    remote = get_remote_receipt(url, dry_run=dry_run)
    log.debug(f"{banner}published receipt: {remote}")

    is_newer = remote.is_newer(local)
    if is_newer:
        log.info(f"{banner}new version found: {remote.version} ({remote.date})")
    else:
        log.info(
            f"{banner}[bold green]success[/]: you have the latest version ([bold cyan]{remote.version}[/])"
        )
    return is_newer, local, remote


def run(args: Args) -> int:
    """Main entry point for `cosmofy updater check`."""
    args.setup_logger()
    log.warning("EXPERIMENTAL: `cosmofy updater` operations are experimental")
    try:
        assert args.ensure_bundle() and args.bundle
        check(
            ZipFile(args.bundle, "r"),
            receipt_url=args.receipt_url,
            dry_run=args.dry_run,
        )
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.updater.check", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
