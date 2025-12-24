#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
import logging
import sys

# pkg
from cosmofy.args import global_options
from cosmofy.args import GlobalArgs
from cosmofy.baton import arg
from cosmofy.baton import Command

from .add import cmd as add
from .check import cmd as check
from .remove import cmd as remove


log = logging.getLogger(__name__)

usage = f"""\
EXPERIMENTAL: Manage a bundle's self-updater.

Usage: cosmofy updater [OPTIONS] <COMMAND>

Commands:
  add                       add self-updater to a bundle
  remove                    remove self-updater from a bundle
  check                     check if the bundle has updates

{global_options}
"""


@dataclass
class Args(GlobalArgs):
    __doc__ = usage
    command: str = arg("", positional=True)  # optional so we can show usage


def run(_: Args) -> int:
    """Main entry point for `cosmofy updater`."""
    # NOTE: only called when there was no subcommand found
    cmd.show_usage()
    return 0


cmd = Command(
    "cosmofy.updater",
    Args,
    run,
    subcommands={
        "add": add,
        "remove": remove,
        "rm": remove,
        "check": check,
    },
)

if __name__ == "__main__":
    sys.exit(cmd.main())
