"""Command-line arguments."""

# std
from __future__ import annotations
from os import environ as ENV
from pathlib import Path
import dataclasses
import logging

log = logging.getLogger(__name__)

DEFAULT_PYTHON_URL = "https://cosmo.zip/pub/cosmos/bin/python"
"""Default URL to download python from."""

COSMOFY_PYTHON_URL = ENV.get("COSMOFY_PYTHON_URL", "")
"""URL to download python from."""

COSMOFY_NO_CACHE = ENV.get("COSMOFY_NO_CACHE", "")
"""Whether to disable cache."""

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "cosmofy"
"""Default cache directory."""

COSMOFY_CACHE_DIR = ENV.get("COSMOFY_CACHE_DIR", "")
"""Path to cache directory."""

RECEIPT_URL = ENV.get("RECEIPT_URL", "")
"""Default receipt URL."""

RELEASE_URL = ENV.get("RELEASE_URL", "")
"""Default release URL."""

USAGE = f"""cosmofy: Cosmopolitan Python Bundler

USAGE

  cosmofy
    [--help] [--version] [--debug] [--dry-run] [--self-update]
    [--input PATH | --clone | --download URL] [--cache PATH]
    [--output PATH] [--args STRING]
    [<add>...] [--exclude GLOB]... [--remove GLOB]...
    [--receipt PATH] [--receipt-url URL] [--release-url URL]
    [--release-version STRING]

GENERAL

  -h, --help        Show this help message and exit.
  --version         Show program version and exit.
  --self-update     Update `cosmofy` to the latest version.
  -q, --quiet...    Show quiet output.
  -v, --verbose...  Show verbose output.
  --dry-run         Do not make any file system changes.

INPUT

  -i PATH, --input PATH
    Start with an existing file.

  --clone
    Start with a copy of the current executable (Cosmopolitan build only).
    In a Cosmopolitan build, this is the default.

  --download
    Start with Cosmopolitan Python from `--python-url`.
    In a non-Cosmopolitan build, this is the default.

  --python-url URL
    URL from which to download Cosmopolitan Python.
    [default: {DEFAULT_PYTHON_URL}]
    [env: COSMOFY_PYTHON_URL={COSMOFY_PYTHON_URL}]

  --no-cache
    Do not read or save to the cache.
    [env: COSMOFY_NO_CACHE={COSMOFY_NO_CACHE}]

  --cache-dir PATH
    Directory in which to cache Cosmopolitan Python downloads.
    [default: {str(DEFAULT_CACHE_DIR).replace(str(Path.home()), "~")}]
    [env: COSMOFY_CACHE_DIR={COSMOFY_CACHE_DIR}]

OUTPUT

  -o PATH, --output PATH
    Path to output file.
    [default: `<main_module>`]

    `<main_module>` is the first module with a `__main__.py` or file with an
    `if __name__ == "__main__"` line.

FILES

  --args STRING
    Cosmopolitan Python arguments.
    [default: `"-m <main_module>"`]

    If NOT using the self-updater, all python options are supported:
    https://docs.python.org/3/using/cmdline.html

    If using the self-updater only a subset is supported:
    https://github.com/metaist/cosmofy#supported-python-cli

  --add GLOB, <add>
    One or more glob-like patterns to add. Folders are recursively added.
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
  to make the resulting bundle capable of updating itself. You
  must supply at least `--receipt-url` or `--release-url`.

  In addition to building the bundle, there will be a second output
  which is a JSON file (called a receipt) that needs to be uploaded
  together with the bundle.

  If the bundle is run with `--self-update` anywhere in the arguments,
  `cosmofy.updater` will run. It will compare it's internal build
  date with the date at `--receipt-url` and will download any updates, if
  they exist.

  Otherwise, the bundle will run as normal by calling `--args`

  NOTE: The updater will alter `--args` so that it gets called first.
  It supports most Python Command Line interface options (like `-m`).
  For a full list see: https://github.com/metaist/cosmofy#supported-python-cli

  --receipt PATH
    Set the path for the JSON receipt.
    [default: `<output>.json`]

  --receipt-url URL
    URL to the published receipt.
    [default: --release-url + .json]
    [env: RECEIPT_URL={RECEIPT_URL}]

  --release-url URL
    URL to the file to download.
    [default: --receipt-url without .json]
    [env: RELEASE_URL={RELEASE_URL}]

  --release-version STRING
    Release version.
    [default: first version-like string in `$(${{output}} --version)`]
"""


@dataclasses.dataclass
class Args:
    help: bool = False
    """Whether to show usage."""

    version: bool = False
    """Whether to show version."""

    cosmo: bool = False
    """(internal) Whether we are running inside a Cosmopolitan build."""

    quiet: int = 0
    """How quiet should the output be?"""

    verbose: int = 0
    """How verbose should the output be?"""

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

    # input

    input: Path | None = None
    """Existing file to start with."""

    clone: bool = False
    """Whether to clone the current executable."""

    download: bool = False
    """Whether to download python."""

    python_url: str = COSMOFY_PYTHON_URL or DEFAULT_PYTHON_URL
    """URL from which to download Cosmopolitan Python."""

    no_cache: bool = COSMOFY_NO_CACHE.lower() in ["1", "true"]
    """Whether to disable cache."""

    cache_dir: Path = Path(COSMOFY_CACHE_DIR or DEFAULT_CACHE_DIR)
    """Directory for caching downloads."""

    # output

    output: Path | None = None
    """Path to the output file."""

    # files

    args: str = ""
    """Args to pass to Cosmopolitan python."""

    add: list[str] = dataclasses.field(default_factory=list)
    """Globs to add."""

    exclude: list[str] = dataclasses.field(default_factory=list)
    """Globs to exclude."""

    remove: list[str] = dataclasses.field(default_factory=list)
    """Globs to remove."""

    # self-updater

    receipt: Path | None = None
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

    def set_prop(self, arg: str, argv: list[str]) -> list[str]:
        prop = arg[2:].replace("-", "_")

        # bool
        if arg in [
            "--cosmo",
            "--help",
            "--version",
            "--dry-run",
            "--no-cache",
        ]:
            setattr(self, prop, True)

        # int
        elif arg in ["--quiet", "--verbose"]:
            setattr(self, prop, getattr(self, prop) + 1)

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
            setattr(self, prop, argv.pop(0))

        # path
        elif arg in ["--input", "--cache-dir", "--output", "--script", "--receipt"]:
            if not argv:
                raise ValueError(f"Expected argument for option: {arg}")
            setattr(self, prop, Path(argv.pop(0)))

        # list[str]
        elif arg in ["--add", "--exclude", "--remove"]:
            if not argv:
                raise ValueError(f"Expected argument for option: {arg}")
            getattr(self, prop).append(argv.pop(0))

        # unknown
        else:
            raise ValueError(f"Unknown option: {arg}")
        return argv

    @staticmethod
    def parse(argv: list[str]) -> Args:
        args = Args()
        alias: dict[str, str] = {
            "-h": "--help",
            # i/o
            "-i": "--input",
            "-o": "--output",
            # logs
            "-q": "--quiet",
            "-v": "--verbose",
            # files
            "-a": "--add",
            "-x": "--exclude",
            "--rm": "--remove",
        }
        while argv:
            if argv[0].startswith("-"):
                arg = argv.pop(0)
                arg = alias.get(arg, arg)

            if arg.startswith("--"):
                argv = args.set_prop(arg, argv)
            else:
                for _arg in arg[1:]:
                    arg = f"-{_arg}"
                    arg = alias.get(arg, arg)
                    argv = args.set_prop(arg, argv)

        # input
        if args.input and not args.output:
            args.output = args.input

        # self-updater
        if args.add_updater and not args.receipt_url and not args.release_url:
            raise ValueError("--receipt-url or --release-url required for updater")
        if not args.receipt_url and args.release_url:
            args.receipt_url = args.release_url + ".json"
        elif not args.release_url and args.receipt_url:
            args.release_url = args.receipt_url.replace(".json", "")
        return args
