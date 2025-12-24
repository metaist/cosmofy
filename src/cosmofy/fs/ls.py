#!/usr/bin/env python
# TODO When mypy learns that `zipfile.Path.at` exists, remove next line.
# mypy: disable-error-code="attr-defined"

# std
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from operator import attrgetter
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Iterator
from typing import Literal
from zipfile import Path as ZipPath
from zipfile import ZipInfo
import logging
import stat
import sys

# pkg
from cosmofy.args import common_args
from cosmofy.args import CommonArgs
from cosmofy.args import global_options
from cosmofy.baton import arg
from cosmofy.baton import Command
from cosmofy.zipfile2 import ZipFile2

from . import expand_glob
from . import shell_match

log = logging.getLogger(__name__)

usage = f"""\
List contents of a Cosmopolitan bundle.

Usage: cosmofy fs ls <BUNDLE> [OPTIONS] [FILE]...

Arguments:
{common_args}
  [FILE]...                 one or more file patterns to show

Filter options:
  -a, --all                 show entries whose name starts with `.`
  -B, --ignore-backups      hide entries whose name ends with `~`
      --hide <PATTERN>      hide matching entries, unless --all
  -I, --ignore <PATTERN>    hide matching entries, even with --all

Sort options:
  -r, --reverse             reverse the sort order
      --sort <MODE>         [choices: none, name, size, time, extension]
                            [default: name]

Output options:
  -l, --long                show permissions, size, and modified date
  -h, --human-readable      show sizes using powers of 1024 like 1K 2M 3G etc.
      --si                  show sizes using powers of 1000 (implies -h)

{global_options.replace("-h,", "   ")}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage

    # positional
    file: list[str] = arg(list, positional=True)
    """Files to show information about."""

    # filter
    all: bool = arg(False, short="-a")
    """Whether to show entries that start with `.`"""

    ignore_backups: bool = arg(False, short="-B")
    """Hide entries that end with `~`"""

    hide: list[str] = arg(list)
    """Hide entries, **unless** with `--all`"""

    ignore: list[str] = arg(list, short="-I")
    """Hide entries, **even** with `--all`"""

    # sort
    reverse: bool = arg(False, short="-r")
    """Whether to reverse the sort."""

    sort: Literal["none", "name", "size", "time", "extension"] = arg("name")
    """How to sort the list."""

    # output
    long: bool = arg(False, short="-l")
    """Whether to use a long listing format."""

    human_readable: bool = arg(False, short="-h")
    """Whether to use human-readable sizes."""

    si: bool = arg(False)
    """Whether to use 1000 instead of 1024 for human-readable chunks."""


def human_size(n: float, si: bool = False) -> str:
    """Return a number of bytes in a human readable way."""
    chunk = 1000.0 if si else 1024.0
    units = (
        ("b", "k", "m", "g", "t", "p", "e", "z", "y")
        if si
        else ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")
    )
    n = float(n)
    for u in units:
        if abs(n) < chunk or u in ["y", "Y"]:
            if u in ["b", "B"]:
                return f"{int(n)}{u}"
            s = f"{n:.1f}".rstrip("0").rstrip(".")
            return f"{s}{u}"
        n /= chunk
    return ""


def ls_time(dt: datetime, *, now: datetime | None = None) -> str:
    """Return a date/time representation similar to `ls`."""
    if now is None:
        now = datetime.now(dt.tzinfo)
    six_months = now - timedelta(days=182)

    mon = dt.strftime("%b")
    day = f"{dt.day:2d}"

    if six_months <= dt <= now and dt.year == now.year:
        hm = dt.strftime("%H:%M")
        return f"{mon} {day} {hm}"
    else:
        year = f"{dt.year:4d}"
        return f"{mon} {day}  {year}"


@dataclass
class Runner:
    bundle: ZipFile2
    args: Args

    def should_include(self, name: str) -> bool:
        """Return `True` if we should include this item."""
        args = self.args
        if any(shell_match(name, pat) for pat in args.ignore):  # always hide
            return False
        if args.all:
            return True
        elif any(shell_match(name, pat) for pat in args.hide):  # hide, if not --all
            return False
        elif name.startswith("."):  # hide .name, if not --all
            return False
        return True

    def get_zipinfo(self, path: ZipPath) -> ZipInfo:
        """Return `ZipInfo` for a path or create a synthetic record."""
        return self.bundle.NameToInfo.get(path.at, ZipInfo(path.at))

    def get_files(self) -> Iterator[ZipInfo]:
        """Iterate over files in a bundle, hiding entries as appropriate."""
        args = self.args
        root = ZipPath(self.bundle)
        seen: set[str] = set()
        names = self.bundle.namelist()

        for pat in args.file:
            for item in expand_glob(names, pat):
                path = root / item
                if item != "" and not path.exists():
                    raise FileNotFoundError(f"No such file or directory: {item}")

                if item != "":  # send the thing itself
                    if path.at not in seen and self.should_include(path.name):
                        seen.add(path.at)
                        yield self.get_zipinfo(path)

                if path.is_dir():
                    for sub in path.iterdir():
                        if sub.at not in seen and self.should_include(sub.name):
                            seen.add(sub.at)
                            yield self.get_zipinfo(sub)

    @staticmethod
    def get_extension(f: ZipInfo) -> tuple[str, str, str]:
        """Return string for extension sorting."""
        parts = f.filename.rstrip("/").split("/")
        if f.filename.endswith("/"):  # is dir
            return "/".join(parts[:-1]), "", parts[-1]

        name = parts[-1]
        stem, ext = name, ""
        if "." in name:
            stem, ext = name.rsplit(".", 1)
        return "/".join(parts[:-1]), ext, stem

    def sort(self, files: Iterable[ZipInfo]) -> Iterator[ZipInfo]:
        """Sort the selected files."""
        if self.args.sort == "none":
            yield from files
            return

        key: Callable[[ZipInfo], Any]
        reverse = self.args.reverse
        match self.args.sort:
            case "name":
                key = attrgetter("filename")  # default
            case "size":
                key = attrgetter("file_size")
                reverse = not reverse  # biggest first
            case "time":
                key = attrgetter("date_time")
                reverse = not reverse  # newest first
            case "extension":
                key = self.get_extension
            case _:  # pragma: no cover
                raise ValueError(f"Unknown option for `--sort`: {self.args.sort}")

        items = sorted(files, key=key, reverse=reverse)
        yield from items

    def format(self, f: ZipInfo) -> str:
        """Prepare info for printing."""
        args = self.args
        line: list[str] = []
        if args.long:
            line.append(f"{stat.filemode(f.external_attr >> 16)} ")

            if args.human_readable or args.si:
                line.append(f"{human_size(f.file_size, args.si):>10} ")
                # line.append(f"{human_size(f.compress_size, args.si):>10} ")
            else:
                line.append(f"{f.file_size:>10} ")
                # line.append(f"{f.compress_size:>10} ")

            line.append(f"{ls_time(datetime(*f.date_time))} ")

        line.append(f.filename)
        return "".join(line)

    def run(self) -> None:
        """List all files in a bundle."""
        for f in self.sort(self.get_files()):
            print(self.format(f))


def run(args: Args) -> int:
    "Entry point for `cosmofy fs ls`."
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle
        if args.dry_run:
            log.info(f"{args.banner}list: {args.bundle}")
            return 0

        if args.ignore_backups:
            # https://www.gnu.org/software/coreutils/manual/html_node/Which-files-are-listed.html#index-_002dB
            args.ignore.extend(["*~", ".*~"])

        if not args.file:
            args.file.extend([""])  # root directory

        # good to go
        with ZipFile2(args.bundle) as bundle:
            Runner(bundle, args).run()
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.ls", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
