#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from getpass import getpass
import logging
import sys

# pkg
from . import expand_glob
from . import fs_common_args
from . import FsCommonArgs
from ..args import global_options
from ..args import show_error
from ..baton import arg
from ..baton import Command
from ..zipfile2 import ZipFile2


log = logging.getLogger(__name__)

usage = f"""\
Print contents of a file within a Cosmopolitan bundle.

Usage: cosmofy fs cat <bundle> [options] <file>...

Arguments:
{fs_common_args}
  <file>...                 one or more file patterns to show

Options:
  -p, --prompt              whether to prompt for a decryption password

{global_options}
"""


@dataclass
class Args(FsCommonArgs):
    file: list[str] = arg(list, positional=True, required=True)
    """Patterns of files to print."""

    prompt: bool = arg(False, short="-p")
    """Whether to prompt for a password."""


def show_files(bundle: ZipFile2, args: Args) -> None:
    password: bytes | None = None
    if args.prompt:
        password = getpass().encode("utf-8")

    names = bundle.namelist()
    for pat in args.file:
        for name in expand_glob(names, pat):
            if name.endswith("/"):  # ignore directories
                continue
            print(bundle.read(name, password).decode("utf-8"), flush=True)


def run(args: Args) -> int:
    """Entry point for `cosmofy fs cat`."""
    try:
        assert args.ensure_bundle() and args.bundle
        if args.dry_run:
            for pattern in args.file:
                print(f"[DRY RUN] <show contents of {pattern} in {args.bundle}>")
            return 0

        # good to go
        bundle = ZipFile2(args.bundle)
        show_files(bundle, args)
    except Exception as e:
        show_error(args, log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.cat", Args, run, usage)

if __name__ == "__main__":
    sys.exit(cmd.main())
