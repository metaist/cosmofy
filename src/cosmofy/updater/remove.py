#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from os import environ as ENV
from pathlib import Path
from shutil import which
from zipfile import is_zipfile
from zipfile import Path as ZipPath
import logging
import re
import shlex
import subprocess
import sys

# pkg
from cosmofy.fs import expand_glob
from ..args import common_args
from ..args import CommonArgs
from ..args import global_options
from ..baton import Command
from ..baton import arg
from ..fs.args import get_args
from ..fs.args import set_args
from ..zipfile2 import ZipFile2
from .add import COSMOFY_NO_ARGS
from .add import PATH_COSMOFY
from cosmofy.fs.rm import remove_path

log = logging.getLogger(__name__)

ARGS_PREFIXES: list[str] = [
    "-m cosmofy.updater.run",  # 0.2.0
    "-m cosmofy.updater",  # 0.1.0
]

usage = f"""\
Remove cosmofy self-updater from a cosmofy bundle.

Usage: cosmofy updater remove <BUNDLE> [OPTIONS]

Arguments:
{common_args}

Process options:
      --no-args             skip setting `.args`
                            [env: COSMOFY_NO_ARGS={COSMOFY_NO_ARGS}]

{global_options}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage
    no_args: bool = arg(False, env="COSMOFY_NO_ARGS")


def remove_arg_prefix(python_args: str) -> str:
    """Remove cosmofy updater prefix, if any."""
    for prefix in ARGS_PREFIXES:
        if python_args.startswith(prefix):
            return python_args[len(prefix) :].strip()
    return python_args


def run(args: Args) -> int:
    """Entry point for `cosmofy updater remove`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle

        bundle = ZipFile2(args.bundle, mode="a")
        for name in expand_glob(bundle.namelist(), PATH_COSMOFY + "*"):
            remove_path(bundle, name, force=True, recursive=True, dry_run=args.dry_run)

        if not args.no_args:
            set_args(bundle, remove_arg_prefix(get_args(bundle)), dry_run=args.dry_run)
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.updater.remove", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
