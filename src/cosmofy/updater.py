#!/usr/bin/env python
"""Cosmofy self-updater.

This program is bundled into Cosmopolitan Python apps
to give them the ability to update themselves.
See: https://github.com/metaist/cosmofy

Usage: {program} --self-update [--help] [--version] [--debug]

Options:

  --self-update
    Indicates that this self-updater should run instead of the usual
    program.

  -h, --help
   Show this message and exit.

  --debug
    Show debug messages.

Environment:

  RECEIPT_URL={RECEIPT_URL}
    If set, this URL will override the built-in URL for downloading
    update metadata.

  RELEASE_URL={RELEASE_URL}
    If set, this URL will override the published URL for downloading
    the update.
"""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from email.utils import parsedate_to_datetime
from importlib._bootstrap_external import SourceFileLoader  # type: ignore
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from urllib.request import Request
from urllib.request import urlopen
import code as repl
import hashlib
import logging
import re
import runpy
import subprocess
import sys
import traceback
__version__ = "0.1.0"
__pubdate__ = "unpublished"

log = logging.getLogger(__name__)

DEFAULT_HASH = "sha256"
"""Default hashing algorithm."""

CHUNK_SIZE = 65536
"""Default chunk size."""

RE_VERSION = re.compile(rb"\d+\.\d+\.\d+(-[\da-zA-Z-.]+)?(\+[\da-zA-Z-.]+)?")
"""Regex for a semver version string."""

RECEIPT_SCHEMA = "https://metaist.com/schema/2024-09-17-cosmofy.schema.json"
"""URI of Cosmofy Receipt Schema."""

RECEIPT_KIND = Literal["embedded", "published"]
"""Valid values for `Receipt.kind`."""

RECEIPT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
"""Regex to validate `Receipt.date`."""

RECEIPT_ALGO = re.compile(r"^[a-z0-9-_]+$")
"""Regex to validate `Receipt.algo`."""

RECEIPT_HASH = re.compile(r"^[a-f0-9]+$")
"""Regex to validate `Receipt.hash`."""


@dataclass
class Receipt:
    """Asset metadata."""

    schema: str = RECEIPT_SCHEMA
    """Receipt schema."""

    kind: RECEIPT_KIND = get_args(RECEIPT_KIND)[0]
    """Whether this receipt is full (published) or partial (embedded)."""

    date: datetime = dataclasses.field(default=now)
    """UTC date/time of this receipt."""

    algo: str = DEFAULT_HASH
    """Hashing algorithm."""

    hash: str = ""
    """Asset hash."""

    receipt_url: str = ""
    """Asset receipt URL."""

    release_url: str = ""
    """Asset download URL."""

    version: str = ""
    """Asset version."""

    def is_newer(self, other: Receipt) -> bool:
        """Return `True` if this receipt is not newer `other`."""
        return self.date > other.date

    def __str__(self) -> str:
        """Return `json`-encoded string."""
        return json.dumps(self.asdict())

    def asdict(self) -> Dict[str, str]:
        """Return `dict` representation of the receipt."""
        return {
            "$schema": self.schema,
            "kind": self.kind,
            "date": self.date.isoformat()[:19] + "Z",
            "algo": self.algo,
            "hash": self.hash,  # maybe empty
            "receipt_url": self.receipt_url,
            "release_url": self.release_url,
            "version": self.version,  # maybe empty
        }

    def is_valid(self) -> bool:
        """Return `True` if there are no issues with the receipt."""
        issues = Receipt.find_issues(self.asdict())
        return not sum((v for v in issues.values()), [])

    @staticmethod
    def find_issues(data: Dict[str, str]) -> Dict[str, List[str]]:
        """Return field names by issue that occurred during validation."""
        issues: Dict[str, List[str]] = {"missing": [], "unknown": [], "malformed": []}
        rules: Dict[str, Checker] = {
            "$schema": lambda v: v == RECEIPT_SCHEMA,
            "kind": lambda v: v in get_args(RECEIPT_KIND),
            "date": lambda v: bool(RECEIPT_DATE.match(v)),
            "algo": lambda v: bool(RECEIPT_ALGO.match(v)),
            "hash": lambda v: bool(RECEIPT_HASH.match(v)),
            "receipt_url": lambda v: bool(v.strip()),
            "release_url": lambda v: bool(v.strip()),
            "version": lambda v: bool(v.strip()),
        }
        embedded: Dict[str, Checker] = {
            "hash": lambda v: isinstance(v, str),
            "version": lambda v: isinstance(v, str),
        }

        kind = data.get("kind", "embedded")
        issues["unknown"] = [name for name in data if name not in rules]
        for name, rule in rules.items():
            if name not in data:
                issues["missing"].append(name)
                continue
            if name in embedded and kind == "embedded":
                rule = embedded[name]
            if not rule(data[name]):
                issues["malformed"].append(name)
        return issues

    def update(self, **values: str) -> Receipt:
        """Update this receipt with several values."""
        for name, value in values.items():
            if name == "date":
                self.date = datetime.fromisoformat(value)
            else:
                setattr(self, name, value)
        return self

    def update_from(self, other: Receipt, *names: str, **values: str) -> Receipt:
        """Update this receipt from another receipt."""
        for name in names:
            setattr(self, name, getattr(other, name))
        return self.update(**values)

    @staticmethod
    def from_dict(data: Dict[str, str]) -> Receipt:
        """Return receipt from a `dict`."""
        issues = Receipt.find_issues(data)
        if sum((v for v in issues.values()), []):
            raise ValueError("Invalid receipt", issues)

        _data = {**data}  # copy to prevent modification
        schema = _data.pop("$schema")
        date = datetime.fromisoformat(_data.pop("date"))
        kind: RECEIPT_KIND = (  # mypy can't detect this properly
            "published" if _data.pop("kind") == "published" else "embedded"
        )
        return Receipt(schema=schema, kind=kind, date=date, **_data)

    @staticmethod
    def from_url(url: str) -> Receipt:
        """Return a Receipt from a URL."""
        with urlopen(url) as response:
            return Receipt.from_dict(json.load(response))

    @staticmethod
    def from_path(path: Path, version: str = "", algo: str = DEFAULT_HASH) -> Receipt:
        """Return receipt for a `path`. Calls `$ {path} --version`"""
        digest = hashlib.new(algo, path.read_bytes()).hexdigest()
        if not version:
            cmd = (f"{path.resolve()} --version",)
            out = subprocess.run(cmd, capture_output=True, check=True, shell=True)
            if match := RE_VERSION.search(out.stdout):
                version = match.group().decode("utf-8")
        return Receipt(algo=algo, hash=digest, version=version)

    """Download `url` to path."""
    log.info(f"Downloading {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, path.open("wb") as output:
        while chunk := response.read(chunk_size):
            output.write(chunk)
    return path


def download_if_newer(url: str, path: Path, chunk_size: int = CHUNK_SIZE) -> Path:
    """Download `url` to `path` if `url` is newer."""
    exists = path.exists()
    need_download = not exists  # guess: exists => already downloaded
    if exists:
        local = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        response = urlopen(Request(url, method="HEAD"))
        remote = parsedate_to_datetime(response.headers.get("Last-Modified"))
        need_download = remote > local  # only download if newer
    return download(url, path, chunk_size) if need_download else path


def create_receipt(
    path: Path,
    algo: str = DEFAULT_HASH,
    date: Optional[datetime] = None,
    version: str = "",
) -> Dict[str, str]:
    """Create JSON receipt data."""
    digest = getattr(hashlib, algo)()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            digest.update(chunk)

    date = date or datetime.now()
    if not version:
        out = subprocess.run(
            f"{path.resolve()} --version", shell=True, capture_output=True, check=True
        ).stdout
        if match := RE_VERSION.search(out):
            version = match.group().decode("utf-8")

    return {
        "algo": algo,
        "hash": digest.hexdigest(),
        "date": date.isoformat()[:19] + "Z",
        "version": version,
    }


def self_update(url: str, path: Path) -> int:
    print("SELF UPDATE", url, path)
    return 0


@dataclass
class PythonArgs:
    """Subset of python command-line arguments.

    See: https://docs.python.org/3/using/cmdline.html
    """

    c: Optional[str] = None
    """Command to execute."""

    i: bool = False
    """Interactive mode."""

    m: Optional[str] = None
    """Module name."""

    q: bool = False
    """No copyright and version messages."""

    V: bool = False
    """Version information."""

    VV: bool = False
    """Verbose version information."""

    script: Optional[str] = None
    """Script to execute."""

    argv: List[str] = field(default_factory=list)
    """Remaining arguments to <script>, <module>, or <command>."""

    @staticmethod
    def parse(argv: List[str]) -> PythonArgs:
        """Parse a subset of python command-line args."""
        args = PythonArgs()
        UNSUPPORTED = """
            -? -h --help --help-env --help-xoptions --help-all
            -b -B --check-hash-based-pycs -d -E -I -O -OO -P -R
            -s -S -u -v -W -x -X
        """.split()
        while argv:
            arg = argv.pop(0)
            if arg.startswith("--"):
                pass
            elif arg.startswith("-") and len(arg) > 2:  # expand
                argv = [f"-{a}" for a in arg[1:]] + argv
                continue

            if arg in ["-c", "-m"]:  # flags with an argument
                if not argv:
                    raise ValueError(f"Argument expected for the {arg} option")
                setattr(args, arg[1:], argv.pop(0))
                args.argv += argv  # whatever is left
                # NOTE: for -m it should be the full path to the module
                args.argv.insert(0, arg)
                break  # remainder are argv
            elif arg in ["-i", "-q"]:  # <bool> flags
                setattr(args, arg[1:], True)
            elif arg in ["-"]:
                args.c = sys.stdin.read()
                if sys.stdin.isatty():
                    args.i = True
                args.argv += argv  # whatever is left
                args.argv.insert(0, "-")
                break  # remainder are argv
            elif arg in ["-V", "--version"]:
                if args.V:
                    args.VV = True
                else:
                    args.V = True
            elif arg in UNSUPPORTED:
                raise ValueError(f"Unsupported (but valid) python option: {arg}")
            elif arg.startswith("-"):
                raise ValueError(f"Unknown option: {arg}")
            else:  # <script>
                args.script = arg
                args.argv += argv
                args.argv.insert(0, arg)  # "script name as given on the command line"
                break  # remainder are argv

        if not any([args.c, args.i, args.m, args.V, args.script]):
            args.i = True
            args.argv.insert(0, "")
        return args


def run_python(argv: List[str]) -> int:
    """Simulate running python with the given args."""
    try:
        args = PythonArgs.parse(argv)
    except ValueError as e:
        log.error(e)
        return 2

    if args.V:
        version = sys.version
        if not args.VV:
            version = ".".join(str(x) for x in sys.version_info[:3])
        print(f"Python {version}")
        return 0

    if isinstance(__builtins__, dict):
        loader = __builtins__["__loader__"]
    else:  # pragma: no cover
        # During testing, __builtins__ is a dict.
        loader = __builtins__.__loader__

    local: Dict[str, object] = {
        "__name__": "__main__",
        "__doc__": None,
        "__package__": None,
        "__loader__": loader,
        "__spec__": None,
        "__annotations__": {},
        "__builtins__": __builtins__,
    }

    sys.argv = args.argv
    code = 0
    try:
        if args.c:  # execute in the context of the locals
            args.q = True
            exec(args.c, local, local)
        elif args.m:
            args.q = True
            runpy.run_module(args.m, local, "__main__", alter_sys=True)
        elif args.script:
            args.q = True
            local["__loader__"] = SourceFileLoader
            runpy.run_path(args.script, local, "__main__")
    except Exception as e:
        code = 1
        # NOTE: We skip the calling frame to emulate the CLI better.
        tb = sys.exc_info()[2]
        tb_next = tb.tb_next if tb else tb
        print("".join(traceback.format_exception(e.__class__, e, tb_next)), end="")

    if args.i:  # after <command>, <module>, or <script>, enter interactive mode
        code = 0
        info = 'Type "help", "copyright", "credits" or "license" for more information.'
        banner = f"Python {sys.version} on {sys.platform}\n{info}"
        if args.q:
            banner = ""
        repl.interact(banner=banner, local=local, exitmsg="")

    return code


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for self-updater."""
    args = argv or sys.argv[1:]
    if "--self-update" in args:
        if "-h" in args or "--help" in args:
            assert __doc__
            doc = __doc__.format(
                program=Path(sys.executable).name,
                RECEIPT_URL=ENV.get("RECEIPT_URL", ""),
                RELEASE_URL=ENV.get("RELEASE_URL", ""),
            )
            print(doc)
            return 0
        if "--version" in args:
            print(f"cosmofy.updater {__version__} ({__pubdate__})")
            return 0
        level = logging.DEBUG if "--debug" in args else logging.INFO
        logging.basicConfig(level=level, format=log_normal)
        return self_update(Path(sys.executable))
    return run_python(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
