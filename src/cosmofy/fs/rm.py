#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from zipfile import Path as ZipPath
import logging
import sys

# pkg
from cosmofy.args import common_args
from cosmofy.args import CommonArgs
from cosmofy.args import get_banner
from cosmofy.args import global_options
from cosmofy.baton import arg
from cosmofy.baton import Command
from cosmofy.zipfile2 import ZipFile2

log = logging.getLogger(__name__)

usage = f"""\
Remove files from a Cosmopolitan bundle.

Usage: cosmofy fs rm <BUNDLE> [OPTIONS] <FILE>...

Arguments:
{common_args}
  <FILE>...                 files to remove

  tip: Use `--` to separate options from filenames that start with `-`
  Example: cosmofy fs rm bundle.zip -- -weird-filename.txt

Options:
  -f, --force               ignore nonexistent files
  -r, --recursive           recursively remove directories

{global_options}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage
    file: list[str] = arg(list, positional=True, required=True, action="extend")
    force: bool = arg(False, short="-f")
    recursive: bool = arg(False, short="-r")  # TODO: support -R


def remove_path(
    bundle: ZipFile2,
    name: str,
    *,
    force: bool = False,
    recursive: bool = False,
    # global
    dry_run: bool = False,
    level: int = logging.INFO,
) -> None:
    """Remove `path` from `bundle`."""
    banner = get_banner(dry_run)
    for_real = not dry_run

    path = ZipPath(bundle.filename or "", name)
    if not path.exists():
        if force:
            return
        raise FileNotFoundError(f"cannot find {name}")

    if path.is_file():
        if for_real:
            bundle.remove(name)
        log.log(level, f"{banner}removed: {name}")
    elif path.is_dir():
        if not recursive:
            err = f"cannot remove directory {name}"
            err += "\n  tip: use --recursive"
            raise Exception(err)
        for item in path.iterdir():
            remove_path(
                bundle,
                item.at,  # type: ignore
                force=force,
                recursive=recursive,
                dry_run=dry_run,
            )
        if name in bundle.NameToInfo:  # dir actually has an entry
            if for_real:
                bundle.remove(name)
            log.log(level, f"{banner}removed: {name}")


def run(args: Args) -> int:
    """Entry point for `cosmofy fs rm`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle
        # good to go

        bundle = ZipFile2(args.bundle, mode="a")
        for name in args.file:
            # TODO: We need to fix `expand_glob` to only read up to the / before we can use it here.
            remove_path(
                bundle,
                name,
                force=args.force,
                recursive=args.recursive,
                dry_run=args.dry_run,
            )
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.rm", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
