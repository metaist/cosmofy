#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from getpass import getpass
import logging
import sys

# pkg
from . import expand_glob
from ..args import common_args
from ..args import CommonArgs
from ..args import global_options
from ..baton import arg
from ..baton import Command
from ..zipfile2 import ZipFile2


log = logging.getLogger(__name__)

usage = f"""\
Print contents of a file within a Cosmopolitan bundle.

Usage: cosmofy fs cat <BUNDLE> [OPTIONS] <FILE>...

Arguments:
{common_args}
  <FILE>...                 one or more file patterns to show

Options:
  -p, --prompt              prompt for a decryption password

{global_options}
"""


@dataclass
class Args(CommonArgs):
    file: list[str] = arg(list, positional=True, required=True)
    """Patterns of files to print."""

    prompt: bool = arg(False, short="-p")
    """Whether to prompt for a password."""


def show_files(bundle: ZipFile2, args: Args) -> None:
    banner = args.banner

    password: bytes | None = None
    if args.for_real and args.prompt:
        password = getpass().encode("utf-8")

    names = bundle.namelist()
    for pat in args.file:
        for name in expand_glob(names, pat):
            if name.endswith("/"):  # ignore directories
                continue
            if args.for_real:
                print(bundle.read(name, password).decode("utf-8"), flush=True)
            else:
                print(f"{banner}<show contents of {name}>", flush=True)


def run(args: Args) -> int:
    """Entry point for `cosmofy fs cat`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle
        bundle = ZipFile2(args.bundle)
        show_files(bundle, args)
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.cat", Args, run, usage)

if __name__ == "__main__":
    sys.exit(cmd.main())
