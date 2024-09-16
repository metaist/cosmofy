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

USAGE = f"""cosmofy: Cosmopolitan Python Bundler

USAGE

  cosmofy
    [--help] [--version] [--debug] [--dry-run] [--self-update]
    [--python-url URL] [--cache PATH] [--clone]
    [--output PATH] [--receipt]
    [--args STRING] [--add-updater URL]
    <add>... [--exclude GLOB]... [--remove GLOB]...

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

    If omitted, it will be `<main_module>.com` where `<main_module>`
    where `<main_module>` is the first module with a `__main__.py` or file with  checks for `__name__ == "__main__"`.

  --receipt
    Create a JSON file with the `--output` date, version, and hash. Written
    to `<output>.json`.

FILES

  --args STRING
    Cosmopolitan Python arguments.

    If omitted, it will be `"-m <main_module>"` where `<main_module>` is
    the the same as the default for `--output`.

  --add-updater URL
    Add `cosmofy.updater` which implements a `--self-update` argument by
    checking for and downloading updates from `URL`.

    NOTE: The updater supports most interface options for `--args`, but
    not all of them. For a list of supported options see:
    https://github.com/metaist/cosmofy#supported-python-cli

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
    """Whether we are running inside a Cosmopolitan build."""

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

    # files

    args: str = ""
    """Args to pass to Cosmopolitan python."""

    output: Optional[Path] = None
    """Path to the output file."""

    receipt: bool = False
    """Whether to create a JSON file with the output date, version, and hash."""

    add_updater: str = ""
    """Add updater to a given URL."""

    add: List[str] = dataclasses.field(default_factory=list)
    """Globs to add."""

    exclude: List[str] = dataclasses.field(default_factory=list)
    """Globs to exclude."""

    remove: List[str] = dataclasses.field(default_factory=list)
    """Globs to remove."""

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
                "--receipt",
                "--version",
            ]:
                setattr(args, prop, True)

            # str
            elif arg in ["--add-updater", "--args", "--python-url"]:
                if not argv:
                    raise ValueError(f"Expected argument for option: {arg}")
                setattr(args, prop, argv.pop(0))

            # path
            elif arg in ["--cache", "--output"]:
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

        args.for_real = not args.dry_run
        if args.cache and args.cache.name.lower() in ["0", "false"]:
            args.cache = None
        return args
