#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from zipfile import is_zipfile
import logging
import sys

# pkg
from cosmofy.args import global_options
from cosmofy.args import GlobalArgs
from cosmofy.baton import Command
from cosmofy.updater.run import self_update


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

        self_update(Path(sys.executable))
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.self.update", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
