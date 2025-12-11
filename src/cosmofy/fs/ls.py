#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from fnmatch import fnmatchcase
from operator import attrgetter
from typing import Callable
from typing import Iterable
from typing import Iterator
from typing import Literal
import logging
import stat
import sys
import zipfile

# pkg
from . import fs_common_arglist
from . import fs_common_args
from . import FsCommonArgs
from .__main__ import FsArgs
from ..args import append
from ..args import Arg
from ..args import extend
from ..args import global_arglist
from ..args import global_options
from ..args import parse_args
from ..args import short_usage
from ..args import store
from ..zipfile2 import ZipFile2

log = logging.getLogger(__name__)

usage = f"""\
List contents of a Cosmopolitan bundle.

Usage: cosmofy fs ls <bundle> [options] [<file>...]

Arguments:
  <file>...                 one or more file patterns to show
{fs_common_args}

Filter options:
  -a, --all                 show entries whose name starts with `.`
  -B, --ignore-backups      hide entries whose name ends with `~`
      --hide <PATTERN>      hide matching entries, unless `--all`
  -I, --ignore <PATTERN>    hide matching entries, even with `--all`

Sort options:
  -r, --reverse             reverse the sort order
      --sort <MODE>         one of: `none`, `name` (default),
                            `size`, `time`, `extension`

Output options:
  -l, --long                show permissions, size, and modified date
  -h, --human-readable      show sizes using powers of 1024 like 1K 2M 3G etc.
      --si                  show sizes using powers of 1000 (implies -h)

{global_options.replace("-h,", "   ")}
"""

arglist: list[Arg] = [
    *global_arglist,
    *fs_common_arglist,
    # positional
    Arg("file", kind=str, action=extend, required=False),
    # filter
    Arg("--all", "-a"),
    Arg("--ignore-backups", "-B"),
    Arg("--hide", kind=str, action=append),
    Arg("--ignore", "-I", kind=str, action=append),
    # sort
    Arg("--reverse", "-r"),
    Arg("--sort", kind=str, action=store),
    # output
    Arg("--long", "-l"),
    Arg("--human-readable", "-h"),  # NOTE: conflicts with `--help`
    Arg("--si"),
]


@dataclass
class Args(FsArgs, FsCommonArgs):
    # positional

    file: list[str] = field(default_factory=list)
    """Files to show information about."""

    # filter

    all: bool = False
    """Whether to show entries that start with `.`"""

    ignore_backups: bool = False
    """Hide entries that end with `~`"""

    hide: list[str] = field(default_factory=list)
    """Hide entries, **unless** with `--all`"""

    ignore: list[str] = field(default_factory=list)
    """Hide entries, **even** with `--all`"""

    # sort

    reverse: bool = False
    """Whether to reverse the sort."""

    sort: Literal["none", "name", "size", "time", "extension"] = "name"
    """How to sort the list."""

    # output

    long: bool = False
    """Whether to use a long listing format."""

    human_readable: bool = False
    """Whether to use human-readable sizes."""

    si: bool = False
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


def shell_match(name: str, pat: str) -> bool:
    """Match following weird starts-with-dot rules."""
    if name.startswith(".") and not pat.startswith("."):
        return False
    return fnmatchcase(name, pat)


@dataclass
class Ls:
    bundle: ZipFile2
    args: Args

    def expand_glob(self, pat: str) -> Iterator[str]:
        """Return all file names in the bundle that match the pattern."""
        if "*" in pat or "?" in pat:
            items = (name for name in self.bundle.namelist() if shell_match(name, pat))
            yield from items
        else:
            yield pat

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

    def get_zipinfo(self, path: zipfile.Path) -> zipfile.ZipInfo:
        """Return `ZipInfo` for a path or create a synthetic record."""
        return self.bundle.NameToInfo.get(path.at, None) or zipfile.ZipInfo(path.at)

    def get_files(self) -> Iterator[zipfile.ZipInfo]:
        """Iterate over files in a bundle, hiding entries as appropriate."""
        args = self.args
        root = zipfile.Path(self.bundle)
        seen: set[str] = set()

        for pat in args.file:
            for item in self.expand_glob(pat):
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
    def get_extension(f: zipfile.ZipInfo) -> tuple[str, str, str]:
        """Return string for extension sorting."""
        parts = f.filename.rstrip("/").split("/")
        if f.filename.endswith("/"):  # is dir
            return "/".join(parts[:-1]), "", parts[-1]

        name = parts[-1]
        stem, ext = name, ""
        if "." in name:
            stem, ext = name.rsplit(".", 1)
        return "/".join(parts[:-1]), ext, stem

    def sort(self, files: Iterable[zipfile.ZipInfo]) -> Iterator[zipfile.ZipInfo]:
        """Sort the selected files."""
        if self.args.sort == "none":
            yield from files

        reverse = self.args.reverse
        if self.args.sort == "name":
            key: attrgetter[str] = attrgetter("filename")  # default
        elif self.args.sort == "size":
            key: attrgetter[int] = attrgetter("file_size")
            reverse = not reverse  # biggest first
        elif self.args.sort == "time":
            key: attrgetter[tuple] = attrgetter("date_time")
            reverse = not reverse  # newest first
        elif self.args.sort == "extension":
            key = self.get_extension
        else:
            raise ValueError(f"Unknown option for `--sort`: {self.args.sort}")

        items = sorted(files, key=key, reverse=reverse)
        yield from items

    def format(self, f: zipfile.ZipInfo) -> str:
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


def main(argv: list[str] | None = None, parsed: FsArgs | None = None) -> int:
    """Entry point for `cosmofy fs ls`."""
    try:
        argv = (argv or sys.argv)[1:]
        args = Args()
        if parsed:
            args = replace(args, **asdict(parsed))
        args, argv = parse_args(args, argv, arglist)
        if args.show_help(usage, log):
            return 0

        assert args.ensure_bundle() and args.bundle
        if args.dry_run:
            print(f"[DRY RUN] <list contents of {args.bundle}>")
            return 0

        if args.ignore_backups:
            # https://www.gnu.org/software/coreutils/manual/html_node/Which-files-are-listed.html#index-_002dB
            args.ignore.extend(["*~", ".*~"])

        if not args.file:
            args.file.extend([""])  # root directory

        # good to go
        bundle = ZipFile2(args.bundle)
        Ls(bundle, args).run()
    except ValueError as e:
        log.error(e)
        print(short_usage(usage))
        return 1
    except Exception as e:
        if args.verbosity > 1:
            log.exception(e)
        else:
            log.error(e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
