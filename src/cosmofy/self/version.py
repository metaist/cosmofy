#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from importlib.metadata import version
import json
import logging
import sys

# pkg
from cosmofy.args import global_options
from cosmofy.args import GlobalArgs
from cosmofy.args import OUTPUT_FORMAT
from cosmofy.baton import arg
from cosmofy.baton import COLOR_MODE
from cosmofy.baton import Command
from cosmofy.baton import render_tags


log = logging.getLogger(__name__)

usage = f"""\
Display `cosmofy`'s version.

Usage: cosmofy self version [OPTIONS]

Options:
      --short               only print the version

{global_options}
"""


@dataclass
class Args(GlobalArgs):
    __doc__ = usage
    short: bool = arg(False)


def get_version(pkg: str = "cosmofy") -> dict[str, str]:
    """Return package metadata."""
    return {"package_name": pkg, "version": version(pkg)}


def print_version(
    *,
    short: bool = False,
    output_format: OUTPUT_FORMAT = "text",
    color: COLOR_MODE = "auto",
) -> str:
    """Print version information and return the text printed."""
    result = ""
    data = get_version()
    if output_format == "json":
        result = json.dumps(data, indent=2)
    else:
        result = f"[cyan]{data['version']}[/]"
        if not short:
            result = f"{data['package_name']} {result}"
        result = render_tags(result, color=color)

    print(result)  # do not log
    return result


def run(args: Args) -> int:
    """Entry point for `cosmofy self version`."""
    args.setup_logger()
    try:
        print_version(
            short=args.short,
            output_format=args.output_format,
            color=args.color,
        )
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.self.version", Args, run)

if __name__ == "__main__":  # pragma: no cover
    sys.exit(cmd.main())
