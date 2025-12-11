#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from getpass import getpass
import logging
import sys

# pkg
from . import expand_glob
from . import fs_common_arglist
from . import fs_common_args
from . import FsCommonArgs
from .__main__ import FsArgs
from ..args import Arg
from ..args import extend
from ..args import global_arglist
from ..args import global_options
from ..args import parse_args
from ..args import short_usage
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

arglist: list[Arg] = [
    *global_arglist,
    *fs_common_arglist,
    Arg("file", kind=str, action=extend, required=True),
    Arg("--prompt", "-p"),
]


@dataclass
class Args(FsArgs, FsCommonArgs):
    file: list[str] = field(default_factory=list)
    """Patterns of files to print."""

    prompt: bool = False
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


def main(argv: list[str] | None = None, parsed: FsArgs | None = None) -> int:
    """Entry point for `cosmofy fs cat`."""
    argv = (argv or sys.argv)[1:]
    args = Args()

    try:
        if parsed:
            args = replace(args, **asdict(parsed))
        args, argv = parse_args(args, argv, arglist)
        if args.show_help(usage, log):
            return 0

        assert args.ensure_bundle() and args.bundle
        if args.dry_run:
            for pattern in args.file:
                print(f"[DRY RUN] <show contents of {pattern} in {args.bundle}>")
            return 0

        # good to go
        bundle = ZipFile2(args.bundle)
        show_files(bundle, args)
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
