#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from shlex import split
import logging
import sys


# pkg
from ..args import common_args
from ..args import CommonArgs
from ..args import global_options
from ..baton import arg
from ..baton import Command
from ..zipfile2 import ZipFile2


log = logging.getLogger(__name__)

usage = f"""\
Get or set the special `.args` files in a Cosmopolitan bundle.

These are the arguments to the Cosmopolitan Python.

Usage: cosmofy fs args <BUNDLE> [OPTIONS] [<VAL>]

Arguments:
{common_args}
  <VAL>                     value to set (if omitted, current value is printed)

{global_options}
"""


@dataclass
class Args(CommonArgs):
    val: str = arg("", positional=True, required=False)


def get_args(bundle: ZipFile2) -> str:
    """Return a single-line representation of the `.args` file."""
    name = ".args"
    info = bundle.NameToInfo.get(name)
    if info is None:
        return ""
    return bundle.read(".args").decode("utf-8").replace("\n", " ")


def set_args(bundle: ZipFile2, val: str) -> str:
    """Set the value of the `.args` file."""
    if bundle.NameToInfo.get(".args") is not None:
        bundle.remove(".args")
    bundle.add_file(".args", "\n".join(split(val)))
    return val


def run(args: Args) -> int:
    """Entry point for `cosmofy fs args`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle
        bundle = ZipFile2(args.bundle, "a")
        if args.val:
            if args.for_real:
                print(set_args(bundle, args.val))
            else:
                print(f"{args.banner}<set .args in {args.bundle}>")
        else:
            print(get_args(bundle))
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.args", Args, run, usage)

if __name__ == "__main__":
    sys.exit(cmd.main())
