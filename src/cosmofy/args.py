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
    [--help] [--version] [--debug] [--dry-run]
    [--python-url URL] [--cache PATH] [--clone]
    [--output PATH] [--args STRING]
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

CACHE

  --python-url URL
    URL from which to download Cosmopolitan Python.
    [env: COSMOFY_PYTHON_URL={COSMOFY_PYTHON_URL}]

  --cache PATH
    Directory in which to cache Cosmopolitan Python downloads.
    Use `false` or `0` to disable caching.
    [env: COSMOFY_CACHE_DIR={COSMOFY_CACHE_DIR}]

  --clone
    EXPERIMENTAL: Whether to obtain python by cloning `cosmofy` and
    removing itself instead of downloading it from `--python-url`

FILES

  -o PATH, --output PATH
    Path to output file (see below for default value).

  --receipt
    Whether to create a JSON file with the output date, version, and hash.

  --args STRING
    Cosmopolitan Python arguments (see below for default value).

  --add GLOB, <add>
    At least one glob-like patterns to add. Folders are recursively added.
    Files ending in `.py` will be compiled.

  -x GLOB, --exclude GLOB
    One or more glob-like patterns to exclude from being added.

    By default, "*.egg-info" and "__pycache__" are excluded.

  --rm GLOB, --remove GLOB
    One or more glob-like patters to remove from the output.

    Common things to remove are `pip`, terminal info, and SSL certs:
    $ cosmofy src/my_module --rm 'usr/*' --rm 'Lib/site-packages/pip/*'

NOTES

  When `--args` or `--output` is missing:
    - If `<path>` is a single file:
        --args = "-m <path_without_suffix>"
        --output = "<path_without_suffix>.com"

    - If `<path>` contains a `__main__.py`, the first one encountered:
        --args = "-m <parent_folder>"
        --output = "<parent_folder>.com"

    - If `<path>` contains a `__init__.py`, we search for the first file
      that contains the line `if __name__ == '__main__'`:
        --args = "-m <file_without_suffix>"
        --output = "<file_without_suffix>.com"
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

    paths: List[Path] = dataclasses.field(default_factory=list)
    """Paths to add."""

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
            elif arg in ["--args", "--python-url"]:
                setattr(args, prop, argv.pop(0))

            # path
            elif arg in ["--cache", "--output"]:
                setattr(args, prop, Path(argv.pop(0)))

            # list[str]
            elif arg in ["--add", "--exclude", "--remove"]:
                getattr(args, prop).append(argv.pop(0))

            # unknown
            else:
                raise ValueError(f"Unknown argument: {arg}")

        args.for_real = not args.dry_run
        if args.cache and args.cache.name.lower() in ["0", "false"]:
            args.cache = None
        return args
