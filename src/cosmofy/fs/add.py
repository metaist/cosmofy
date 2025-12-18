#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import logging
import sys
import os

# pkg
from ..args import common_args
from ..args import CommonArgs
from ..args import global_options
from ..baton import arg
from ..baton import Command
from ..zipfile2 import ZipFile2


log = logging.getLogger(__name__)

usage = f"""\
Add files to a Cosmopolitan bundle.

Usage: cosmofy fs add <BUNDLE> [OPTIONS] <FILE>...

Arguments:
{common_args}
  <FILE>...                 files relative to current directory to add

Options:
  -f, --force               overwrite existing files
      --chdir <PATH>        change to this directory before adding
      --dest                prefix to add in the bundle
                            Most python packages go into `Lib/site-packages`

{global_options}
"""


@dataclass
class Args(CommonArgs):
    file: list[str] = arg(list, positional=True, required=True, action="extend")
    chdir: Path | None = arg(None)
    dest: str = arg("")
    force: bool = arg(False, short="-f")
    # compile_bytecode: bool = arg(False)


def add_path(bundle: ZipFile2, args: Args, src: Path, dest: str) -> None:
    banner = args.banner
    if not src.exists():
        raise FileNotFoundError(f"Cannot find file: {src.resolve()}")

    if src.is_file():
        if args.for_real:
            if bundle.NameToInfo.get(dest) is not None:
                if args.force:
                    bundle.remove(dest)
                else:
                    raise FileExistsError(
                        f"File already exists: {dest}\nHint: use -f to overwrite."
                    )
            bundle.add_file(dest, src.read_bytes())
        print(f"{banner}add: {dest}")
    elif src.is_dir():
        for item in src.iterdir():
            add_path(bundle, args, item, dest + f"/{item.name}")


def add_files(bundle: ZipFile2, args: Args) -> None:
    """Add files to the bundle."""
    original = Path.cwd()
    if args.chdir:
        log.debug(f"change directory: {args.chdir}")
        os.chdir(args.chdir)

    root = Path.cwd()
    prefix = str(root)
    for name in args.file:
        dest = args.dest + name.removeprefix(prefix)
        add_path(bundle, args, Path(name), dest)

    if args.chdir:
        log.debug(f"change directory: {original}")
        os.chdir(original)


def run(args: Args) -> int:
    """Entry point for `cosmofy fs add`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle

        args.dest = args.dest.strip("/")
        # NOTE: We remove the leading slash so that "/Lib" properly
        # becomes "Lib". We remove the trailing slash so we can
        # add bits properly.

        # good to go
        bundle = ZipFile2(args.bundle, mode="a")
        add_files(bundle, args)
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.add", Args, run, usage)

if __name__ == "__main__":
    sys.exit(cmd.main())
