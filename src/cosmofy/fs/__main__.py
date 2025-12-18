#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
import logging
import sys

# pkg
from .add import cmd as add
from .args import cmd as args
from .cat import cmd as cat
from .ls import cmd as ls
from .rm import cmd as rm
from ..args import global_options
from ..args import GlobalArgs
from ..baton import arg
from ..baton import Command


log = logging.getLogger(__name__)

usage = f"""\
Cosmopolitan file system tool.

Usage: cosmofy fs [OPTIONS] <COMMAND>

Commands:
  ls                        list files in bundle
  cat                       print file contents
  add                       add files to bundle
  rm                        remove files from bundle
  args                      get/set special `.args` file in bundle

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
        "ls": ls,
        "cat": cat,
        "add": add,
        "rm": rm,
        "args": args,
    },
)

if __name__ == "__main__":
    sys.exit(cmd.main())
