#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from zipfile import Path as ZipPath
import logging
import sys

# pkg
from . import fs_common_args
from . import FsCommonArgs
from ..args import global_options
from ..baton import arg
from ..baton import Command
from ..zipfile2 import ZipFile2


log = logging.getLogger(__name__)

usage = f"""\
Remove files from a Cosmopolitan bundle.

Usage: cosmofy fs rm <bundle> [options] <file>...

Arguments:
{fs_common_args}
  <file>...                 files to remove

Options:
  -f, --force               ignore nonexistent files
  -r, --recursive           recursively remove directories

{global_options}
"""


@dataclass
class Args(FsCommonArgs):
    __doc__ = usage
    file: list[str] = arg(list, positional=True, required=True, action="extend")
    force: bool = arg(False, short="-f")
    recursive: bool = arg(False, short="-r")  # TODO: support -R


def remove_path(bundle: ZipFile2, args: Args, name: str) -> None:
    """Remove a path from a bundle."""
    banner = args.banner

    assert args.bundle  # for type check
    path = ZipPath(args.bundle, name)
    if not path.exists():
        if args.force:
            return
        raise FileNotFoundError(f"Cannot find {name}")

    if path.is_file():
        if args.for_real:
            bundle.remove(name)
        log.info(f"{banner}remove: {name}")
    elif path.is_dir():
        if not args.recursive:
            raise Exception(f"Cannot remove directory {name}. Hint: use -r")
        for item in path.iterdir():
            remove_path(bundle, args, item.at)
        if name in bundle.NameToInfo:  # dir actually has an entry
            if args.for_real:
                bundle.remove(name)
            log.info(f"{banner}remove: {name}")


def run(args: Args) -> int:
    """Entry point for `cosmofy fs rm`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle
        # good to go

        bundle = ZipFile2(args.bundle, mode="a")
        for name in args.file:
            # TODO: We need to fix `expand_glob` to only read up to the / before we can use it here.
            remove_path(bundle, args, name)
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.rm", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
