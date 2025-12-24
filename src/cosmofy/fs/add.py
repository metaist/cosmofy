#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import logging
import sys
import os

# pkg
from cosmofy.args import common_args
from cosmofy.args import CommonArgs
from cosmofy.args import get_banner
from cosmofy.args import global_options
from cosmofy.baton import arg
from cosmofy.baton import Command
from cosmofy.zipfile2 import ZipFile2

from .rm import remove_path


log = logging.getLogger(__name__)

usage = f"""\
Add files to a Cosmopolitan bundle.

Usage: cosmofy fs add <BUNDLE> [OPTIONS] <FILE>...

Arguments:
{common_args}
  <FILE>...                 files relative to current directory to add

  tip: Use `--` to separate options from filenames that start with `-`
  Example: cosmofy fs add bundle.zip -- -weird-filename.txt

Options:
  -f, --force               overwrite existing files
      --chdir <PATH>        change to this directory before adding
      --dest                prefix to add in the bundle
                            Most python packages go into `Lib/site-packages`

{global_options}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage
    file: list[str] = arg(list, positional=True, required=True, action="extend")
    chdir: Path | None = arg(None)
    dest: str = arg("")
    force: bool = arg(False, short="-f")
    # compile_bytecode: bool = arg(False)


def sanitize_zip_path(dest: str) -> str:
    """Normalize and validate a zip archive path.

    - Converts backslashes to forward slashes
    - Removes leading slashes (no absolute paths)
    - Rejects path traversal attempts (`..`)

    Raises:
        ValueError: If path contains `..` segments
    """
    if "\x00" in dest:
        raise ValueError(f"refusing path with null byte: {dest!r}")

    clean = dest.replace("\\", "/")
    if clean.startswith("/"):
        log.warning(f"Stripping leading '/' from absolute path: {dest}")

    parts = [p for p in clean.split("/") if p and p != "."]
    if any(p == ".." for p in parts):
        raise ValueError(f"refusing path with '..': {dest}")
    return "/".join(parts)


def add_data(
    bundle: ZipFile2,
    data: str | bytes | bytearray,
    dest: str,
    *,
    force: bool = False,
    # global
    dry_run: bool = False,
    level: int = logging.INFO,
) -> None:
    """Add `data` to `bundle` at location `dest`."""
    dest = sanitize_zip_path(dest)
    banner = get_banner(dry_run)
    for_real = not dry_run

    if bundle.NameToInfo.get(dest) is not None:  # already exists
        if force:
            remove_path(
                bundle,
                dest,
                force=force,
                recursive=False,
                dry_run=dry_run,
                level=level,
            )
        else:
            err = f"{banner}file already exists: {dest}"
            err += "\n  tip: use --force to overwrite it"
            raise FileExistsError(err)

    if for_real:
        bundle.add_file(dest, data)
    log.log(level, f"{banner}added {dest}")


def add_path(
    bundle: ZipFile2,
    src: Path,
    dest: str,
    *,
    force: bool = False,
    # global
    dry_run: bool = False,
    level: int = logging.INFO,
    _seen: set[str] | None = None,
) -> None:
    """Add `src` to `bundle` at location `dest`."""
    _seen = _seen or set()
    real = str(src.resolve())
    if real in _seen:  # already done
        log.warning(f"skipping circular symlink: {src}")
        return
    _seen.add(real)

    dest = sanitize_zip_path(dest)
    banner = get_banner(dry_run)
    if not src.exists():
        raise FileNotFoundError(f"{banner}cannot find file: {src.resolve()}")

    if src.is_file():
        add_data(
            bundle, src.read_bytes(), dest, force=force, dry_run=dry_run, level=level
        )
    elif src.is_dir():
        for item in src.iterdir():
            add_path(
                bundle,
                item,
                dest + f"/{item.name}",
                force=force,
                dry_run=dry_run,
                level=level,
                _seen=_seen,
            )


def add_files(bundle: ZipFile2, args: Args) -> None:
    """Add files to the bundle."""
    original = Path.cwd()
    if args.chdir:
        log.debug(f"change directory: {args.chdir}")
        os.chdir(args.chdir)

    try:
        root = Path.cwd().resolve()
        for name in args.file:
            path = Path(name)
            try:
                rel = path.resolve().relative_to(root)
                dest = str(Path(args.dest) / rel) if args.dest else str(rel)
            except ValueError:
                # Path is not under root, use as-is
                dest = args.dest + name if args.dest else name
            add_path(bundle, Path(name), dest, force=args.force, dry_run=args.dry_run)
    finally:
        if args.chdir:
            log.debug(f"change directory: {original}")
            os.chdir(original)


def run(args: Args) -> int:
    """Entry point for `cosmofy fs add`."""
    args.setup_logger()
    try:
        assert args.ensure_bundle() and args.bundle

        args.dest = args.dest.strip("/")
        # NOTE: We remove the leading slash so that "/Lib" properly
        # becomes "Lib". We remove the trailing slash so we can
        # add bits properly.

        # good to go
        with ZipFile2(args.bundle, mode="a") as bundle:
            add_files(bundle, args)
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.fs.add", Args, run, usage)

if __name__ == "__main__":
    sys.exit(cmd.main())
