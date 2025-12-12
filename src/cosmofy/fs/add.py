#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from pathlib import Path
import logging
import sys
import os

# pkg
from . import fs_common_arglist
from . import fs_common_args
from . import FsCommonArgs
from .__main__ import FsArgs
from ..args import Arg
from ..args import extend
from ..args import store
from ..args import global_arglist
from ..args import global_options
from ..args import parse_args
from ..args import short_usage
from ..zipfile2 import ZipFile2


log = logging.getLogger(__name__)

DEFAULT_DEST = "Lib/site-packages"

usage = f"""\
Add files to a Cosmopolitan bundle.

Usage: cosmofy fs add <bundle> [options] <file>...

Arguments:
{fs_common_args}
  <file>...                 files relative to current directory to add

Options:
      --chdir <PATH>        change to this directory before adding
      --dest                prefix to add in the bundle
        [default: {DEFAULT_DEST}]

{global_options}
"""

arglist: list[Arg] = [
    *global_arglist,
    *fs_common_arglist,
    Arg("file", kind=str, action=extend, required=True),
    Arg("--chdir", kind=Path, action=store),
    Arg("--dest", kind=str, action=store),
    # Arg("--compile-bytecode"),
]


@dataclass
class Args(FsArgs, FsCommonArgs):
    file: list[str] = field(default_factory=list)
    """Patterns of files to add."""

    chdir: Path | None = None
    """Directory to change to before adding."""

    dest: str = DEFAULT_DEST
    """Prefix to add in bundle."""


def add_path(bundle: ZipFile2, src: Path, dest: str, dry_run: bool = False) -> None:
    banner = "[DRY RUN] " if dry_run else ""
    if not src.exists():
        raise FileNotFoundError(f"Cannot find file: {src.resolve()}")

    if src.is_file():
        log.info(f"{banner} add: {dest}")
        if not dry_run:
            bundle.add_file(dest, src.read_bytes())
    elif src.is_dir():
        for item in src.iterdir():
            add_path(bundle, item, dest + f"/{item.name}", dry_run)


def add_files(bundle: ZipFile2, args: Args) -> None:
    """Add files to the bundle."""
    original = Path.cwd()
    if args.chdir:
        log.debug(f"change directory: {args.chdir}")
        os.chdir(args.chdir)

    root = Path.cwd()
    prefix = str(root)
    for pattern in args.file:
        for src in sorted(root.glob(pattern)):
            dest = args.dest + str(src).removeprefix(prefix)
            add_path(bundle, src, dest, args.dry_run)

    if args.chdir:
        log.debug(f"change directory: {original}")
        os.chdir(original)


def main(argv: list[str] | None = None, parsed: FsArgs | None = None) -> int:
    """Entry point for `cosmofy fs add`."""
    argv = (argv or sys.argv)[1:]
    args = Args()

    try:
        if parsed:
            args = replace(args, **asdict(parsed))
        args, argv = parse_args(args, argv, arglist)
        if args.show_help(usage, log):
            return 0

        assert args.ensure_bundle() and args.bundle

        args.dest = args.dest.strip("/")
        # NOTE: We remove the leading slash so that "/Lib" properly
        # becomes "Lib". We remove the trailing slash so we can
        # add bits properly.

        # good to go
        bundle = ZipFile2(args.bundle, mode="a")
        add_files(bundle, args)
    except ValueError as e:
        log.error(e)
        print(short_usage(usage))
        return 1
    except Exception as e:
        if args.verbosity > 1:
            log.exception(e)
        else:
            log.error(e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
