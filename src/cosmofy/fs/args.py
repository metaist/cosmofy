#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
import logging
import shlex
import sys


# pkg
from cosmofy.args import common_args
from cosmofy.args import CommonArgs
from cosmofy.args import get_banner
from cosmofy.args import global_options
from cosmofy.baton import arg
from cosmofy.baton import Command
from cosmofy.zipfile2 import ZipFile2

from .rm import remove_path


log = logging.getLogger(__name__)

usage = f"""\
Get or set the special `.args` files in a Cosmopolitan bundle.

These are the arguments to the Cosmopolitan Python.

Usage: cosmofy fs args <BUNDLE> [OPTIONS] [VAL]

Arguments:
{common_args}
  [VAL]                     value to set (if omitted, current value is printed)

{global_options}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage
    val: str = arg("", positional=True, required=False)


def get_args(bundle: ZipFile2) -> str:
    """Return a single-line representation of the `.args` file."""
    name = ".args"
    info = bundle.NameToInfo.get(name)
    if info is None:
        return ""
    return shlex.join(bundle.read(".args").decode("utf-8").split("\n"))


def set_args(bundle: ZipFile2, val: str, *, dry_run: bool = False) -> str:
    """Set the value of the `.args` file."""
    banner = get_banner(dry_run)
    for_real = not dry_run

    val = val.strip()
    if bundle.NameToInfo.get(".args") is not None:
        remove_path(bundle, ".args", force=True, dry_run=dry_run)
    if for_real:
        bundle.add_file(".args", "\n".join(shlex.split(val)))
    log.info(f"{banner}set `.args` to '{val}'")
    return val


def run(args: Args) -> int:
    """Entry point for `cosmofy fs args`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle
        with ZipFile2(args.bundle, "a") as bundle:
            if args.val:
                set_args(bundle, args.val, dry_run=args.dry_run)
            else:
                print(get_args(bundle), flush=True)  # don't log!
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.args", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
