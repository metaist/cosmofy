#!/usr/bin/env python
"""pythonoid: small simulated python CLI"""

# std
from __future__ import annotations
from importlib._bootstrap_external import SourceFileLoader  # type: ignore
from importlib.util import MAGIC_NUMBER
from os import environ as ENV
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
import code as repl
import dataclasses
import logging
import marshal
import re
import runpy
import sys
import traceback

log = logging.getLogger(__name__)


Pkg = Tuple[str, ...]
"""Package information."""

MODULE_SUFFIXES = (".py", ".pyc")
"""Python module suffixes."""

PACKAGE_STEMS = ("__init__", "__main__")
"""File stems that indicate a python package."""

PACKAGE_FILES = tuple(p + s for p in PACKAGE_STEMS for s in MODULE_SUFFIXES)
"""File names that indicate a python package."""

MAIN_FILES = ("__main__.py", "__main__.pyc")
"""File names that indicate python package has a main."""

RE_MAIN = re.compile(
    rb"""
    (^|\n)if\s*(
    __name__\s*==\s*['"]__main__['"]| # written the normal way
    ['"]__main__['"]\s*==\s*__name__) # written in reverse
    """,
    re.VERBOSE,
)
"""Regex for detecting a main section in `bytes`."""


# https://github.com/python/cpython/blob/3.12/Lib/importlib/_bootstrap_external.py#L79C1-L81C55
def _pack_uint32(x: Union[int, float]) -> bytes:
    """Convert a 32-bit integer to little-endian."""
    return (int(x) & 0xFFFFFFFF).to_bytes(4, "little")


def compile_python(path: Path, source: Optional[bytes] = None) -> bytearray:
    """Return the bytecode."""
    source = path.read_bytes() if source is None else source
    stats = path.stat()
    mtime = stats.st_mtime
    source_size = stats.st_size

    # https://github.com/python/cpython/blob/3.12/Lib/importlib/_bootstrap_external.py#L1059
    code = compile(source, path, "exec", dont_inherit=True, optimize=-1)

    # https://github.com/python/cpython/blob/3.12/Lib/importlib/_bootstrap_external.py#L764
    data = bytearray(MAGIC_NUMBER)
    data.extend(_pack_uint32(0))
    data.extend(_pack_uint32(mtime))
    data.extend(_pack_uint32(source_size))
    data.extend(marshal.dumps(code))
    return data


# https://github.com/python/cpython/blob/32119fc377a4d9df524a7bac02b6922a990361dd/Python/initconfig.c#L233
USAGE = f"""\
usage: {Path(__file__).name} [option] ... [-c cmd | -m mod | file | -] [arg] ...
Options (and corresponding environment variables):
-c cmd : program passed in as string (terminates option list)
-h     : print this help message and exit (also -? or --help)
-i     : inspect interactively after running script; forces a prompt even
         if stdin does not appear to be a terminal; also PYTHONINSPECT=x
-I     : isolate Python from the user's environment (implies -E and -s)
-m mod : run library module as a script (terminates option list)
-q     : don't print version and copyright messages on interactive startup
-V     : print the Python version number and exit (also --version)
         when given twice, print more information about the build

Arguments:
file   : program read from script file
-      : program read from stdin (default; interactive mode if a tty)
arg ...: arguments passed to program in sys.argv[1:]

Python has many more options that pythonoid does not support:
https://docs.python.org/3/using/cmdline.html"""


@dataclasses.dataclass
class PythonArgs:
    """Subset of python command-line arguments.

    See: https://docs.python.org/3/using/cmdline.html
    """

    c: Optional[str] = None
    """Command to execute."""

    h: bool = False
    """Show help."""

    i: bool = ENV.get("PYTHONINSPECT", "") == "x"
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

    argv: List[str] = dataclasses.field(default_factory=list)
    """Remaining arguments to <script>, <module>, or <command>."""

    @staticmethod
    def parse(argv: List[str]) -> PythonArgs:
        """Parse a subset of python command-line args."""
        args = PythonArgs()
        UNSUPPORTED = """
            --help-env --help-xoptions --help-all
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
            elif arg in ["-?", "-h", "--help"]:
                args.h = True
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

        if not any([args.c, args.h, args.i, args.m, args.V, args.script]):
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

    if args.h:
        print(USAGE)
        return 0

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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run_python(sys.argv[1:]))
