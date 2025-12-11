#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from types import ModuleType
import logging
import sys

# pkg
from . import add
from . import cat
from . import ls
from . import rm
from . import set_args
from ..args import Arg
from ..args import global_arglist
from ..args import global_options
from ..args import GlobalArgs
from ..args import parse_args
from ..args import short_usage
from ..args import store

log = logging.getLogger(__name__)

usage = f"""\
Cosmopolitan file system tool.

Usage: cosmofy fs [options] <command>

Commands:
  ls                        list files in bundle
  cat                       print file contents
  add                       add files to bundle
  rm                        remove files from bundle
  set-args                  set special .args file in bundle

{global_options}
"""

arglist: list[Arg] = [
    *global_arglist,
    Arg("command", kind=str, action=store),
]
commands: dict[str, ModuleType] = {
    "ls": ls,
    "cat": cat,
    # "add": add,
    # "rm": rm,
    # "set-args": set_args,
}


@dataclass
class FsArgs(GlobalArgs):
    command: str = ""
    """Subcommand to run."""


def main(argv: list[str] | None = None) -> int:
    """Main entry point for `cosmofy fs`."""
    try:
        argv = (argv or sys.argv)[1:]
        args, argv = parse_args(FsArgs(), argv, arglist, commands=commands)
        if args.show_help(usage, log):
            return 0

        if args.command not in commands:
            raise ValueError(f"Unknown command: {args.command}")
    except ValueError as e:
        log.error(e)
        print(short_usage(usage))
        return 1

    return commands[args.command].main(["fs"] + argv, args)  # type: ignore


if __name__ == "__main__":
    sys.exit(main())
