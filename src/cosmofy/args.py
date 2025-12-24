"""Command-line arguments."""

# std
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from zipfile import is_zipfile
import logging

# pkg
from .baton import arg
from .baton import COLOR_MODE
from .baton import ColorFormatter

DRY_RUN = "[`DRY RUN`] "
"""Banner to display when using `--dry-run`."""


def get_banner(dry_run: bool = False) -> str:
    """Return `DRY_RUN` banner if `dry_run` is `True`."""
    return DRY_RUN if dry_run else ""


log_normal = "%(levelname)s: %(message)s"
log_debug = "[dim]%(name)s.%(funcName)s: [/]%(levelname)s: %(message)s"
log_verbose = "[dim]%(filename)s:%(lineno)s %(funcName)s: [/]%(levelname)s: %(message)s"

log = logging.getLogger(__name__)

global_options = """\
Global options:
  -h, --help                show this help message
  -q, --quiet...            show quiet output
  -v, --verbose...          show verbose output
      --dry-run             do not make any filesystem changes
      --color <COLOR>       control output color
                            [default: auto][choices: auto, always, never]
                            (auto checks `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`,
                            `CLICOLOR_FORCE` and tty support)
""".rstrip()


@dataclass
class GlobalArgs:
    help: bool = arg(False, short="-h")
    quiet: int = arg(0, short="-q", action="count")
    verbose: int = arg(0, short="-v", action="count")
    dry_run: bool = arg(False)
    color: COLOR_MODE = arg(default="auto")

    @property
    def verbosity(self) -> int:
        """Return how verbose vs quiet we should be."""
        return self.verbose - self.quiet

    @property
    def for_real(self) -> bool:
        """Opposite of `dry_run`."""
        return not self.dry_run

    @for_real.setter
    def for_real(self, value: bool) -> None:
        """Set `dry_run`."""
        self.dry_run = not value

    @property
    def banner(self) -> str:
        """Return dry run banner, if required."""
        return get_banner(self.dry_run)

    def setup_logger(self) -> None:
        """Ensure logging is configured properly."""
        level = self.verbosity
        if level < 0:
            logging.disable(logging.CRITICAL)
        elif level > 0:
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)
            fmt = log_verbose if level > 1 else log_debug
            formatter = ColorFormatter(fmt)
            for handler in root_logger.handlers:
                handler.setFormatter(formatter)
        log.debug(self)

    def show_error(self, log: logging.Logger, e: Exception) -> None:
        "Display an error."
        if self.verbosity > 1:
            log.exception(e)
        else:
            log.error(e)


common_args = """\
  <BUNDLE>                  Cosmopolitan file bundle
""".rstrip()


@dataclass
class CommonArgs(GlobalArgs):
    bundle: Path | None = arg(None, positional=True, required=True)

    def ensure_bundle(self) -> bool:
        """Resolve `bundle` parameter and make sure it exists (in non-dry run)."""
        if self.bundle:
            self.bundle = self.bundle.resolve()

        if self.for_real and (
            self.bundle is None
            or not self.bundle.exists()
            or not is_zipfile(self.bundle)
        ):
            raise FileNotFoundError(f"could not find Cosmopolitan file: {self.bundle}")

        return True
