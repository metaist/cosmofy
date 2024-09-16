#!/usr/bin/env python
"""Self-updater."""

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

log = logging.getLogger(__name__)

DEFAULT_HASH = "sha256"
"""Default hashing algorithm."""

CHUNK_SIZE = 65536
"""Default chunk size."""

RE_VERSION = re.compile(rb"\d+\.\d+\.\d+(-[\da-zA-Z-.]+)?(\+[\da-zA-Z-.]+)?")
"""Regex for a semver version string."""


def download(url: str, path: Path, chunk_size: int = CHUNK_SIZE) -> Path:
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
            f"{path} --version", shell=True, capture_output=True, check=True
        ).stdout
        if match := RE_VERSION.search(out):
            version = match.group().decode("utf-8")

    return {
        "algo": algo,
        "hash": digest.hexdigest(),
        "date": date.isoformat()[:19] + "Z",
        "version": version,
    }


def self_update(src: Path) -> int:
    print("SELF UPDATE")
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
        return self_update(Path(sys.executable))
    return run_python(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
