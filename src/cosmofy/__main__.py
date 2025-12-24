#!/usr/bin/env python
"""cosmofy: Cosmopolitan Python bundler"""

from __future__ import annotations
from dataclasses import dataclass
import logging
import sys

# pkg
from .args import global_options
from .args import GlobalArgs
from .args import log_normal
from .baton import arg
from .baton import ColorFormatter
from .baton import ColorHandler
from .baton import Command
from .bundle import cmd as bundle
from .fs.__main__ import cmd as fs
from .self.__main__ import cmd as self
from .self.version import print_version
from .updater.__main__ import cmd as updater


log = logging.getLogger(__name__)

usage = f"""\
A Cosmopolitan Python bundler.

Usage: cosmofy [OPTIONS] <COMMAND>

Commands:
  bundle                    build and bundle a project
  updater                   install/uninstall bundle self-updater
  fs                        inspect and modify an existing bundle
  self                      manage the `cosmofy` executable

Options:
      --version             display the program version and exit

{global_options}
"""


def setup_logger() -> None:
    """Setup root logger, if needed."""
    root = logging.getLogger()
    if not root.handlers:  # pragma: no cover
        handler = ColorHandler()
        handler.setFormatter(ColorFormatter(log_normal))
        logging.basicConfig(level=logging.INFO, handlers=[handler])


@dataclass
class Args(GlobalArgs):
    command: str = arg("", positional=True)  # optional so we can show usage
    version: bool = arg(False)


def run(args: Args) -> int:
    """Main entry point for `cosmofy`."""
    args.setup_logger()
    if args.version:
        print_version()
        return 0

    # NOTE: only called when there was no subcommand found
    cmd.show_usage()
    return 0


cmd = Command(
    "cosmofy",
    Args,
    run,
    usage,
    {
        "bundle": bundle,
        "updater": updater,
        "fs": fs,
        "self": self,
    },
)


def main() -> None:
    """Main entry point for console scripts."""
    setup_logger()
    sys.exit(cmd.main())


if __name__ == "__main__":  # pragma: no cover
    main()
