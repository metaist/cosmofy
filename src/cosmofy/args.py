"""Command-line arguments."""

# std
from __future__ import annotations
from os import environ as ENV
from pathlib import Path
from typing import List
from typing import Optional
import dataclasses
import logging

log = logging.getLogger(__name__)

COSMOFY_PYTHON_URL = ENV.get(
    "COSMOFY_PYTHON_URL", "https://cosmo.zip/pub/cosmos/bin/python"
)
"""URL to download python from."""

COSMOFY_CACHE_DIR = Path(
    ENV.get("COSMOFY_CACHE_DIR", Path.home() / ".cache" / "cosmofy")
)
"""Path to cache directory."""

RECEIPT_URL = ENV.get("RECEIPT_URL", "")
"""Default receipt URL."""

RELEASE_URL = ENV.get("RELEASE_URL", "")
"""Default release URL."""

USAGE = f"""cosmofy: Cosmopolitan Python Bundler

USAGE

  cosmofy
    [--help] [--version] [--debug] [--dry-run] [--self-update]
    [--python-url URL] [--cache PATH] [--clone]
    [--output PATH] [--args STRING]
    <add>... [--exclude GLOB]... [--remove GLOB]...
    [--receipt PATH] [--receipt-url URL] [--release-url URL]
    [--release-version STRING]

GENERAL

  -h, --help
    Show this help message and exit.

  --version
    Show program version and exit.

  --debug
    Show debug messages.

  -n, --dry-run
    Do not make any file system changes.

  --self-update
    Update `cosmofy` to the latest version.

CACHE

  --python-url URL
    URL from which to download Cosmopolitan Python.
    [env: COSMOFY_PYTHON_URL={COSMOFY_PYTHON_URL}]

  --cache PATH
    Directory in which to cache Cosmopolitan Python downloads.
    Use `false` or `0` to disable caching.
    [env: COSMOFY_CACHE_DIR={COSMOFY_CACHE_DIR}]

  --clone
    Obtain python by cloning `cosmofy` and removing itself instead of
    downloading it from `--python-url`.

OUTPUT

  -o PATH, --output PATH
    Path to output file.
    [default: `<main_module>.com`]

    `<main_module>` is the first module with a `__main__.py` or file with an
    `if __name__ == "__main__"` line.

FILES

  --args STRING
    Cosmopolitan Python arguments.
    [default: `"-m <main_module>"`]

  --add GLOB, <add>
    At least one glob-like patterns to add. Folders are recursively added.
    Files ending in `.py` will be compiled.

  -x GLOB, --exclude GLOB
    One or more glob-like patterns to exclude from being added.

    Common things to exclude are egg files and python cache:
    $ cosmofy src -x "**/*.egg-info/*" -x "**/__pycache__/*"

  --rm GLOB, --remove GLOB
    One or more glob-like patters to remove from the output.

    Common things to remove are `pip`, terminal info, and SSL certs:
    $ cosmofy src/my_module --rm 'usr/*' --rm 'Lib/site-packages/pip/*'

SELF-UPDATER

  Specifying any of the options below will add `cosmofy.updater`
  to make the resulting app capable of updating itself. You
  must supply at least `--receipt-url` or `--release-url`.

  In addition to building the app, there will be a second output
  which is a JSON file (called a receipt) that needs to be uploaded
  together with the app.

  When the app runs, the updater first checks to see if it was called with `--self-update`. If it wasn't, execution continues as normal.
  If it was, the updater checks the published receipt to see if there is a
  newer version of the app and downloads it, if appropriate.

  NOTE: The updater will alter `--args` so that it gets called first.
  It supports most Python Command Line interface options (like `-m`).
  For a full list see: https://github.com/metaist/cosmofy#supported-python-cli

  --receipt PATH
    Set the path for the JSON receipt.
    [default: `<output>.json`]

  --receipt-url URL
    URL to the published receipt.
    [default: <release-url>.json]
    [env: RECEIPT_URL={RECEIPT_URL}]

  --release-url URL
    URL to the file to download.
    [default: <receipt-url-without.json>]
    [env: RELEASE_URL={RELEASE_URL}]

  --release-version STRING
    Release version.
    [default: we run `output --version` and save first version-looking string]
"""


@dataclasses.dataclass
class Args:
    help: bool = False
    """Whether to show usage."""

    version: bool = False
    """Whether to show version."""

    debug: bool = False
    """Whether to show debug messages."""

    cosmo: bool = False
    """(internal) Whether we are running inside a Cosmopolitan build."""

    dry_run: bool = False
    """Whether we should suppress any file-system operations."""

    @property
    def for_real(self) -> bool:
        """Internal value for the opposite of `dry_run`."""
        return not self.dry_run

    @for_real.setter
    def for_real(self, value: bool) -> None:
        """Set dry_run."""
        self.dry_run = not value

    # cache

    python_url: str = COSMOFY_PYTHON_URL
    """URL from which to download Cosmopolitan Python."""

    cache: Optional[Path] = COSMOFY_CACHE_DIR
    """Directory for caching downloads."""

    clone: bool = False
    """Whether to clone `cosmofy` to get python."""

    # output

    output: Optional[Path] = None
    """Path to the output file."""

    # files

    args: str = ""
    """Args to pass to Cosmopolitan python."""

    add: List[str] = dataclasses.field(default_factory=list)
    """Globs to add."""

    exclude: List[str] = dataclasses.field(default_factory=list)
    """Globs to exclude."""

    remove: List[str] = dataclasses.field(default_factory=list)
    """Globs to remove."""

    # self-updater

    receipt: Optional[Path] = None
    """Path to the receipt output."""

    receipt_url: str = RECEIPT_URL
    """URL of latest release receipt."""

    release_url: str = RELEASE_URL
    """URL of latest release download."""

    release_version: str = ""
    """Version of the latest release."""

    @property
    def add_updater(self) -> bool:
        """Internal property on whether to add the updater."""
        return bool(
            self.receipt or self.receipt_url or self.release_url or self.release_version
        )

    @staticmethod
    def parse(argv: List[str]) -> Args:
        args = Args()
        alias = {
            "-h": "--help",
            "-n": "--dry-run",
            "-o": "--output",
            "-x": "--exclude",
            "--rm": "--remove",
        }
        while argv:
            if argv[0].startswith("-"):
                arg = argv.pop(0)
                arg = alias.get(arg, arg)
            else:
                arg = "--add"
            prop = arg[2:].replace("-", "_")

            # bool
            if arg in [
                "--clone",
                "--cosmo",
                "--debug",
                "--dry-run",
                "--help",
                "--version",
            ]:
                setattr(args, prop, True)

            # str
            elif arg in [
                "--args",
                "--python-url",
                "--receipt-url",
                "--release-url",
                "--release-version",
            ]:
                if not argv:
                    raise ValueError(f"Expected argument for option: {arg}")
                setattr(args, prop, argv.pop(0))

            # path
            elif arg in ["--cache", "--output", "--receipt"]:
                if not argv:
                    raise ValueError(f"Expected argument for option: {arg}")
                setattr(args, prop, Path(argv.pop(0)))

            # list[str]
            elif arg in ["--add", "--exclude", "--remove"]:
                if not argv:
                    raise ValueError(f"Expected argument for option: {arg}")
                getattr(args, prop).append(argv.pop(0))

            # unknown
            else:
                raise ValueError(f"Unknown option: {arg}")

        # cache
        if args.cache and args.cache.name.lower() in ["0", "false"]:
            args.cache = None

        # self-updater
        if args.add_updater and not args.receipt_url and not args.release_url:
            raise ValueError("--receipt-url or --release-url required for updater")
        if not args.receipt_url and args.release_url:
            args.receipt_url = args.release_url + ".json"
        elif not args.release_url and args.receipt_url:
            args.release_url = args.receipt_url.replace(".json", "")
        return args
