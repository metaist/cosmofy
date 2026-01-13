#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from zipfile import is_zipfile
import json
import logging
import sys
import zipfile

# pkg
from cosmofy.args import global_options
from cosmofy.args import GlobalArgs
from cosmofy.baton import Command
from cosmofy.updater.check import check
from cosmofy.updater.downloader import download_release


log = logging.getLogger(__name__)

usage = f"""\
Update `cosmofy`.

Usage: cosmofy self update [OPTIONS]

{global_options}
"""


@dataclass
class Args(GlobalArgs):
    __doc__ = usage


def run(args: Args) -> int:
    """Entry point for `cosmofy self update`."""
    args.setup_logger()
    try:
        if not is_zipfile(sys.executable):
            err = "`cosmofy` was not installed in a Cosmopolitan Python bundle"
            err += "\n  tip: see https://github.com/metaist/cosmofy#install"
            raise ValueError(err)

        path = Path(sys.executable)
        with zipfile.ZipFile(path, "r") as bundle:
            is_newer, local, remote = check(bundle, dry_run=args.dry_run)

        updated = False
        if is_newer and args.for_real:
            dest = download_release(remote.release_url, path, remote.hash, remote.algo)
            if dest:
                updated = True
                log.info(f"Updated to {remote.version}")

        if args.output_format == "json":
            print(
                json.dumps(
                    {
                        "update_available": is_newer,
                        "updated": updated,
                        "local_version": local.version,
                        "remote_version": remote.version,
                    },
                    indent=2,
                )
            )
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.self.update", Args, run)

if __name__ == "__main__":  # pragma: no cover
    sys.exit(cmd.main())
