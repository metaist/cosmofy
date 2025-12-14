#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
import logging
import sys

# pkg
from . import add
from . import args
from . import cat
from . import ls
from . import rm
from ..args import global_options
from ..args import GlobalArgs
from ..baton import arg
from ..baton import Command


log = logging.getLogger(__name__)

usage = f"""\
Cosmopolitan file system tool.

Usage: cosmofy fs [options] <command>

Commands:
  ls                        list files in bundle
  cat                       print file contents
  add                       add files to bundle
  rm                        remove files from bundle
  args                      get/set special .args file in bundle

{global_options}
"""


@dataclass
class Args(GlobalArgs):
    command: str = arg("", positional=True)  # optional so we can show usage


def run(_: Args) -> int:
    # NOTE: only called when there was no subcommand found
    cmd.show_usage()
    return 0


cmd = Command(
    "cosmofy.fs",
    Args,
    run,
    usage,
    {
        "ls": ls.cmd,
        "cat": cat.cmd,
        "add": add.cmd,
        "rm": rm.cmd,
        "args": args.cmd,
    },
)

if __name__ == "__main__":
    sys.exit(cmd.main())
