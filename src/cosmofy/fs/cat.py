#!/usr/bin/env python

# std
from __future__ import annotations
from base64 import b64encode
from dataclasses import dataclass
from getpass import getpass
from typing import Any
import json
import logging
import sys

# pkg
from cosmofy.args import common_args
from cosmofy.args import CommonArgs
from cosmofy.args import global_options
from cosmofy.args import OUTPUT_FORMAT
from cosmofy.baton import arg
from cosmofy.baton import Command
from cosmofy.zipfile2 import ZipFile2

from . import expand_glob


log = logging.getLogger(__name__)

usage = f"""\
Print contents of a file within a Cosmopolitan bundle.

Usage: cosmofy fs cat <BUNDLE> <FILE>... [OPTIONS]

Arguments:
{common_args}
  <FILE>...                 one or more file patterns to show

  tip: Use `--` to separate options from filenames that start with `-`
  Example: cosmofy fs cat bundle.zip -- -weird-filename.txt

Options:
  -p, --prompt              prompt for a decryption password
      --output-format NAME  [default: text][choices: text, json]

{global_options}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage
    file: list[str] = arg(list, positional=True, required=True)
    """Patterns of files to print."""

    prompt: bool = arg(False, short="-p")
    """Whether to prompt for a password."""

    output_format: OUTPUT_FORMAT = arg("text")
    """Output format: text or json."""


def file_to_dict(name: str, data: bytes) -> dict[str, Any]:
    """Convert file contents to a dictionary for JSON output."""
    result: dict[str, Any] = {"filename": name, "size": len(data)}
    try:
        result["contents"] = data.decode("utf-8")
        result["encoding"] = "utf-8"
    except UnicodeDecodeError:
        result["contents"] = b64encode(data).decode("ascii")
        result["encoding"] = "base64"
    return result


def show_files(bundle: ZipFile2, args: Args) -> None:
    """Print out the contents of the files."""
    banner = args.banner

    password: bytes | None = None
    if args.for_real and args.prompt:
        password = getpass().encode("utf-8")

    names = bundle.namelist()
    results: list[dict[str, Any]] = []

    for pat in args.file:
        for name in expand_glob(names, pat):
            if name.endswith("/"):  # ignore directories
                continue
            if args.for_real:
                data = bundle.read(name, password)
                if args.output_format == "json":
                    results.append(file_to_dict(name, data))
                else:  # write bytes straight to the terminal
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
            else:
                log.info(f"{banner}show: {name}")

    if args.for_real and args.output_format == "json":
        print(json.dumps(results, indent=2))


def run(args: Args) -> int:
    """Entry point for `cosmofy fs cat`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle
        with ZipFile2(args.bundle) as bundle:
            show_files(bundle, args)
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.cat", Args, run)

if __name__ == "__main__":  # pragma: no cover
    sys.exit(cmd.main())
