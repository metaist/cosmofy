#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
import logging
import sys

# pkg
from ..args import global_options
from ..args import GlobalArgs
from ..baton import arg
from ..baton import Command
from .add import cmd as add
from .check import cmd as check
# from .remove import cmd as remove


log = logging.getLogger(__name__)

usage = f"""\
Manage a bundle's self-updater.

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
    # NOTE: only called when there was no subcommand found
    cmd.show_usage()
    return 0


cmd = Command(
    "cosmofy.self",
    Args,
    run,
    subcommands={
        "add": add,
        # "remove": remove,
        # "rm": remove,
        "check": check,
    },
)

if __name__ == "__main__":
    sys.exit(cmd.main())
