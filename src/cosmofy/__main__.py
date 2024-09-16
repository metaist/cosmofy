"""Main entry point."""

# std
from __future__ import annotations
from typing import List
from typing import Optional
import logging
import sys

# pkg
from . import __pubdate__
from . import __version__
from .args import Args
from .args import USAGE
from .bundler import Bundler

log_normal = "%(levelname)s: %(message)s"
log_debug = "%(name)s.%(funcName)s: %(levelname)s: %(message)s"
log_verbose = " %(filename)s:%(lineno)s %(funcName)s(): %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=log_normal)

log = logging.getLogger(__name__)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    short_usage = "\n" + USAGE[USAGE.find("USAGE") + 5 : USAGE.find("GENERAL")].strip()

    try:
        args = Args.parse((argv or sys.argv)[1:])
    except ValueError as e:
        log.error(e)
        print(short_usage)
        return 1

    if args.debug:
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter(log_debug)
        for handler in logging.getLogger().handlers:
            handler.setFormatter(formatter)
        log.debug(args)

    if args.version:
        print(f"{__version__} ({__pubdate__})", flush=True)
        return 0

    if args.help:
        print(USAGE)
        return 0

    if not args.add:
        log.error("You must specify at least one path to add.")
        print(short_usage)
        return 1

    if args.clone and not args.cosmo:
        log.error(
            "You cannot use --clone outside of a Cosmopolitan build. "
            "See https://github.com/metaist/cosmofy#install"
        )
        return 1

    Bundler(args).run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
