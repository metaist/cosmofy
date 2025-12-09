"""Main entry point."""

# std
from __future__ import annotations
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


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    short_usage = "\n" + USAGE[USAGE.find("USAGE") + 5 : USAGE.find("GENERAL")].strip()

    try:
        args = Args.parse((argv or sys.argv)[1:])
    except ValueError as e:
        log.error(e)
        print(short_usage)
        return 1

    level = args.verbose - args.quiet
    if level < 0:
        logging.disable(logging.CRITICAL)
    elif level > 0:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        fmt = log_debug
        if level > 1:
            fmt = log_verbose
        formatter = logging.Formatter(fmt)
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
        log.debug(args)

    if args.version:
        print(f"{__version__} ({__pubdate__})", flush=True)
        return 0

    if args.help:
        print(USAGE)
        return 0

    Bundler(args).run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
