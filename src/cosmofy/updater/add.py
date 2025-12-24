#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from importlib import metadata
from importlib.metadata import PathDistribution
from os import environ as ENV
from pathlib import Path
from shutil import which
from zipfile import is_zipfile
from zipfile import Path as ZipPath
import logging
import re
import shlex
import subprocess
import sys

# pkg
from cosmofy.args import common_args
from cosmofy.args import CommonArgs
from cosmofy.args import get_banner
from cosmofy.args import global_options
from cosmofy.baton import arg
from cosmofy.baton import Command
from cosmofy.fs.add import add_data
from cosmofy.fs.add import add_path
from cosmofy.fs.args import get_args
from cosmofy.fs.args import set_args
from cosmofy.zipfile2 import ZipFile2

from .pythonoid import PythonArgs
from .receipt import get_version
from .receipt import Receipt


log = logging.getLogger(__name__)

RECEIPT_URL = ENV.get("RECEIPT_URL", "")
"""Override the embedded URL for downloading update metadata."""

RELEASE_URL = ENV.get("RELEASE_URL", "")
"""Override the published URL for downloading the update."""

COSMOFY_NO_COPY = ENV.get("COSMOFY_NO_COPY", "")
"""Skip copying `cosmofy` to bundle."""

COSMOFY_NO_ARGS = ENV.get("COSMOFY_NO_ARGS", "")
"""Skip setting `.args` in bundle."""

ARGS_PREFIX = "-m cosmofy.updater.run"
"""Prefix for updater `.args`"""

PATH_COSMOFY = "Lib/site-packages/cosmofy"
"""Path within zip file to cosmofy package."""

PATH_RECEIPT = f"{PATH_COSMOFY}/.cosmofy.json"
"""Path within the zip file to the local receipt."""

usage = f"""\
EXPERIMENTAL: Add self-updater to a cosmofy bundle.

Usage: cosmofy updater add <BUNDLE> [OPTIONS]

Arguments:
{common_args}

Receipt options:
      --receipt <PATH>      output path to the JSON receipt
                            default is <BUNDLE> + `.json`
      --receipt-url <URL>   URL to the published receipt
                            default is --release-url + `.json`
                            [env: RECEIPT_URL={RECEIPT_URL}]
      --release-url <URL>   URL to the file to download
                            default is --receipt-url without `.json`
                            [env: RELEASE_URL={RELEASE_URL}]
      --release-version <STRING>
                            release version
                            default is $(<BUNDLE> --version)

Process options:
      --no-copy             skip copying `cosmofy` code
                            (e.g., its already a dependency)
                            [env: COSMOFY_NO_COPY={COSMOFY_NO_COPY}]
      --no-args             skip setting `.args`
                            [env: COSMOFY_NO_ARGS={COSMOFY_NO_ARGS}]

read more: https://github.com/metaist/cosmofy#self-updater

{global_options}
"""


@dataclass
class Args(CommonArgs):
    __doc__ = usage
    receipt: Path | None = arg(None)
    receipt_url: str = arg(RECEIPT_URL)
    release_url: str = arg(RELEASE_URL)
    release_version: str = arg("")
    no_copy: bool = arg(False, env="COSMOFY_NO_COPY")
    no_args: bool = arg(False, env="COSMOFY_NO_ARGS")


def get_github_download(name: str) -> str:
    """Return GitHub download url based on the current repo."""
    if not which("git"):
        return ""  # git not installed

    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], text=True, stderr=subprocess.STDOUT
        ).strip()
    except subprocess.CalledProcessError:
        return ""  # not in a git repo or other error

    # SSH forms:
    #   git@github.com:owner/repo.git
    #   ssh://git@github.com/owner/repo.git
    m = re.match(
        r"^(?:ssh://)?git@github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
        url,
    )
    if not m:
        # HTTPS forms:
        #   https://github.com/owner/repo.git
        #   https://github.com/owner/repo
        m = re.match(
            r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$", url
        )

    if not m:
        return ""

    owner = m.group("owner")
    repo = m.group("repo")
    return f"https://github.com/{owner}/{repo}/releases/latest/download/{name}"


def copy_data(
    src: ZipPath, dest: ZipFile2, *, dry_run: bool = False, level: int = logging.INFO
) -> None:
    """Copy data from one zip file to another."""
    if src.is_dir():
        for item in src.iterdir():
            copy_data(item, dest, dry_run=dry_run, level=level)
    elif src.is_file():
        add_data(
            dest,
            src.read_bytes(),
            src.at,  # type: ignore
            force=True,
            dry_run=dry_run,
            level=level,
        )


def from_cosmo(
    bundle: ZipFile2,
    src_path: Path,
    meta_path: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Copy `cosmofy` from the current executable."""
    root = ZipPath(sys.executable)
    copy_data(
        root / "/".join(src_path.parts[2:]),
        bundle,
        dry_run=dry_run,
        level=logging.DEBUG,
    )
    copy_data(
        root / "/".join(meta_path.parts[2:]),
        bundle,
        dry_run=dry_run,
        level=logging.DEBUG,
    )


def from_venv(
    bundle: ZipFile2,
    src_path: Path,
    meta_path: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Copy `cosmofy` from the filesystem into `bundle`."""
    add_path(
        bundle,
        src_path,
        PATH_COSMOFY,
        force=True,
        dry_run=dry_run,
        level=logging.DEBUG,
    )

    meta_dest = f"Lib/site-packages/{meta_path.name}"
    add_path(
        bundle,
        meta_path,
        meta_dest,
        force=True,
        dry_run=dry_run,
        level=logging.DEBUG,
    )


def copy_cosmofy(bundle: ZipFile2, *, dry_run: bool = False) -> None:
    """Copy `cosmofy` package into `bundle`."""
    dist = metadata.distribution("cosmofy")
    src_path = Path(__file__).parent.parent
    site_packages = src_path.parent

    dist_info_name = f"{dist.name}-{dist.version}.dist-info"
    meta_path = site_packages / dist_info_name

    if not meta_path.is_dir():
        if hasattr(dist, "_path") and isinstance(dist, PathDistribution):
            meta_path = Path(str(dist._path))
        else:
            raise FileNotFoundError(f"could not location {dist_info_name}")

    if is_zipfile(sys.executable):
        log.debug("inside cosmo python")
        from_cosmo(bundle, src_path, meta_path, dry_run=dry_run)
    else:
        log.debug("inside python venv")
        from_venv(bundle, src_path, meta_path, dry_run=dry_run)


def add_arg_prefix(python_args: str) -> str:
    """Return updated args."""
    args = python_args.strip()
    try:
        PythonArgs.parse(shlex.split(args))
        if args.startswith(ARGS_PREFIX):  # idempotent
            return args
        return f"{ARGS_PREFIX} {args}".strip()
    except ValueError as e:
        err = f"unsupported python args: '{args}'"
        err += "\n  tip: see https://github.com/metaist/cosmofy#supported-python-cli"
        raise ValueError(err) from e


def write_receipt(
    path: Path,
    bundle: ZipFile2,
    *,
    output: Path,
    receipt_url: str,
    release_url: str,
    release_version: str,
    dry_run: bool = False,
) -> Receipt:
    """Write remote receipt."""
    for_real = not dry_run
    banner = get_banner(dry_run)

    receipt = Receipt(
        receipt_url=receipt_url,
        release_url=release_url,
        version=release_version,
    )
    data = str(receipt)
    log.debug(data)
    if not receipt.is_valid():
        raise ValueError("embedded receipt must be valid")

    add_data(bundle, data, PATH_RECEIPT, force=True, dry_run=dry_run)

    receipt.update_from(
        Receipt.from_path(path, version=release_version),
        "algo",
        "hash",
        "version",
        kind="published",
    )
    data = str(receipt)
    log.debug(data)
    if not receipt.is_valid():
        raise ValueError("published receipt must be valid")

    if for_real:
        output.write_text(data)
    log.info(f"{banner}wrote: {output}")
    return receipt


def run(args: Args) -> int:
    """Entry point for `cosmofy updater add`."""
    args.setup_logger()
    log.warning("EXPERIMENTAL: `cosmofy updater` operations are experimental")
    try:
        assert args.ensure_bundle() and args.bundle
        if not args.receipt:
            args.receipt = args.bundle.with_suffix(f"{args.bundle.suffix}.json")
            log.info(f"infer --receipt: {args.receipt}")

        if not args.release_url:  # try github download
            args.release_url = get_github_download(args.bundle.name)
            log.info(f"infer --release-url: {args.release_url}")
        if not args.receipt_url and not args.release_url:
            err = "at least one of --receipt-url or --release-url is required"
            err += "\n  note: auto-detection only works for GitHub repositories"
            raise ValueError(err)
        if not args.receipt_url:
            args.receipt_url = args.release_url + ".json"
            log.info(f"infer --receipt-url: {args.receipt_url}")
        if not args.release_url:
            if args.receipt_url.endswith(".json"):
                args.release_url = args.receipt_url[:-5]
                log.info(f"infer --release-url: {args.release_url}")
            else:
                err = "could not guess the --release-url, please provide it explicitly"
                raise ValueError(err)

        if not args.release_version:
            args.release_version = get_version(args.bundle)
            log.info(f"infer --release-version: {args.release_version}")
        if not args.release_version:
            err = "could not guess the --release-version, please provide it explicitly"
            raise ValueError(err)

        with ZipFile2(args.bundle, mode="a") as bundle:
            if not args.no_copy:
                copy_cosmofy(bundle, dry_run=args.dry_run)

            if not args.no_args:
                set_args(bundle, add_arg_prefix(get_args(bundle)), dry_run=args.dry_run)

            write_receipt(
                args.bundle,
                bundle,
                output=args.receipt,
                receipt_url=args.receipt_url,
                release_url=args.release_url,
                release_version=args.release_version,
                dry_run=args.dry_run,
            )
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.updater.add", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
