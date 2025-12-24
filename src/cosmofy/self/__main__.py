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
from cosmofy.self.update import cmd as update
from cosmofy.self.version import cmd as version

log = logging.getLogger(__name__)

usage = f"""\
Manage the `cosmofy` executable.

Usage: cosmofy self [OPTIONS] <COMMAND>

Commands:
  update                    update `cosmofy`
  version                   display `cosmofy`'s version

{global_options}
"""


@dataclass
class Args(GlobalArgs):
    __doc__ = usage
    command: str = arg("", positional=True)  # optional so we can show usage


def run(_: Args) -> int:
    """Main entry point for `cosmofy self`."""
    # NOTE: only called when there was no subcommand found
    cmd.show_usage()
    return 0


cmd = Command(
    "cosmofy.self",
    Args,
    run,
    subcommands={
        "update": update,
        "version": version,
    },
)

if __name__ == "__main__":
    sys.exit(cmd.main())
