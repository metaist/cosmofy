#!/usr/bin/env python

# std
from __future__ import annotations
from dataclasses import dataclass
from importlib.metadata import distributions
from os import environ as ENV
from pathlib import Path
from typing import Literal
import json
import logging
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

# pkg
from cosmofy.args import global_options
from cosmofy.args import GlobalArgs
from cosmofy.baton import arg
from cosmofy.baton import Command
from cosmofy.fs.add import add_path
from cosmofy.fs.args import set_args
from cosmofy.updater.downloader import download
from cosmofy.updater.downloader import download_if_newer
from cosmofy.updater.pythonoid import python_call
from cosmofy.updater.receipt import get_version
from cosmofy.zipfile2 import ZipFile2


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

BUNDLE_EXCLUDE = {
    "direct_url.json",
    "uv_build.json",
    "uv_cache.json",
}
"""Exclude uv artifacts."""


usage = f"""\
Build a Python project into a Cosmopolitan bundle.

Usage: cosmofy bundle [OPTIONS]

Input options:
      --entry <NAME>        `console_script` entry points to bundle
      --script <PATH>       paths to bundle

      If neither --entry nor --script is specified, all entry points
      will be bundled. If both are specified, entries will be bundled first.

      --python-url <URL>    URL from which to download Cosmopolitan Python
                            [default: {DEFAULT_PYTHON_URL}]
                            [env: COSMOFY_PYTHON_URL={COSMOFY_PYTHON_URL}]

Output options:
  -o, --output-dir <PATH>   output directory
                            [default: project-root/dist]

Cache options:
  -n, --no-cache            do not read or save to the cache
                            [env: COSMOFY_NO_CACHE={COSMOFY_NO_CACHE}]
      --cache-dir <PATH>    store Cosmopolitan Python downloads
                            [default: {str(DEFAULT_CACHE_DIR).replace(str(Path.home()), "~")}]
                            [env: COSMOFY_CACHE_DIR={COSMOFY_CACHE_DIR}]

{global_options}
"""


@dataclass
class Args(GlobalArgs):
    __doc__ = usage

    # input
    entry: list[str] = arg(list)
    script: list[Path] = arg(list)
    python_url: str = arg(DEFAULT_PYTHON_URL, env="COSMOFY_PYTHON_URL")

    # output
    output_dir: Path | None = arg(None)

    # cache
    no_cache: bool = arg(False, short="-n", env="COSMOFY_NO_CACHE")
    cache_dir: Path = arg(DEFAULT_CACHE_DIR, env="COSMOFY_CACHE_DIR")


def open_zip(file: str | Path, *, mode: Literal["r", "w", "x", "a"] = "r") -> ZipFile2:
    """Wrapper for creating a zip file."""
    return ZipFile2(file, mode, compression=zipfile.ZIP_DEFLATED, compresslevel=9)


def ensure_uv(cmd: str = "uv") -> bool:
    """Raise an error if `uv` is not installed."""
    result = shutil.which(cmd)
    if not result:
        err = f"cannot find command: `{cmd}`"
        err += "\n  tip: see https://docs.astral.sh/uv/getting-started/installation/"
        raise FileNotFoundError(err)
    log.debug(f"`uv` installed at {result}")
    return True


def find_project_root(start: Path | None = None) -> Path:
    """Return the first path that has a `pyproject.toml` in it."""
    start = (start or Path.cwd()).resolve()
    for d in (start, *start.parents):
        if (d / "pyproject.toml").is_file():
            return d
    raise FileNotFoundError("no `pyproject.toml` found")


def venv_site_packages(venv: Path) -> Path:
    """Return the path to `site-packages`."""
    # posix: venv/lib/pythonX.Y/site-packages
    lib = venv / "lib"
    if lib.is_dir():
        candidates = sorted(lib.glob("python*/site-packages"))
        if candidates:
            return candidates[-1]
    # windows: venv/Lib/site-packages
    sp = venv / "Lib" / "site-packages"
    if sp.is_dir():
        return sp
    raise FileNotFoundError(f"cannot find `site-packages` in {venv}")


def console_scripts_from_venv(pkg: str, venv: Path) -> dict[str, str]:
    """Get `console_scripts` for a specific package from a `venv`."""
    sp = venv_site_packages(venv)
    pkg_normalized = pkg.lower().replace("_", "-").replace(".", "-")  # PEP 503
    for dist in distributions(path=[str(sp)]):
        dist_name = dist.metadata["Name"].lower().replace("_", "-").replace(".", "-")
        if dist_name == pkg_normalized:
            return {
                ep.name: ep.value
                for ep in dist.entry_points
                if ep.group == "console_scripts"
            }
    return {}


class Bundler:
    args: Args
    banner: str

    bundle: ZipFile2

    def __init__(self, args: Args):
        """Construct a bundler."""
        self.args = args
        self.banner = args.banner

    # File System

    def fs_copy(self, src: Path, dest: Path) -> Path:
        """Copy a file from `src` to `dest`."""
        log.debug(f"{self.banner}copy: {src} to {dest}")
        if self.args.for_real:
            shutil.copy(src, dest)
        return dest

    def fs_set_executable(self, src: Path) -> Path:
        """Set the executable bit on a file."""
        log.debug(f"{self.banner}chmod +x {src}")
        if self.args.for_real:
            mode = src.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            src.chmod(mode)
        return src

    # cosmopolitan python

    def from_cache(self, src: Path, dest: Path) -> Path:
        """Copy the archive from cache."""
        log.debug(f"{self.banner}download (if newer): {self.args.python_url}")
        if self.args.for_real:
            download_if_newer(self.args.python_url, src)
        return self.fs_set_executable(self.fs_copy(src, dest))

    def from_download(self, dest: Path) -> Path:
        """Download archive."""
        log.debug(f"{self.banner}download (fresh): {self.args.python_url} to {dest}")
        if self.args.for_real:
            download(self.args.python_url, dest)
        return self.fs_set_executable(dest)

    def get_cosmo_python(self, dest: Path) -> Path:
        """Return a `Path` a Cosmopolitan Python executable."""
        if self.args.no_cache:  # fresh
            return self.from_download(dest)
        return self.from_cache(self.args.cache_dir / "python", dest)

    # uv

    def uv_version(self) -> tuple[str, str]:
        """Return package name and version."""
        cmd = ["uv", "version", "--no-build", "--output-format", "json"]
        log.debug(f"{self.banner}run: {shlex.join(cmd)}")
        if self.args.for_real:
            data = json.loads(subprocess.check_output(cmd, text=True))
            name = data.get("package_name", "")
            ver = data.get("version", "")
            return name, ver
        return "", ""

    def uv_sync(
        self,
        *,
        pkg: str,
        version: str,
        venv: Path | None,
        script: Path | None = None,
    ) -> Path:
        """Return the venv used during `uv sync`."""
        args: list[str] = [
            "uv",
            "sync",
            "--python",
            shlex.quote(version),
            "--no-editable",
            "--exact",
            "--output-format",
            "json",
        ]
        env: dict[str, str] = {**ENV}
        if venv:
            env["VIRTUAL_ENV"] = str(venv)
            env["UV_PROJECT_ENVIRONMENT"] = str(venv)

        if script:
            args.extend(["--script", str(script)])
        else:
            args.extend(["--no-default-groups", "--reinstall-package", pkg])

        if self.args.verbosity > 0:
            args.append(f"-{'v' * self.args.verbosity}")
        elif self.args.verbosity < 0:
            args.append(f"-{'q' * abs(self.args.verbosity)}")
        if self.args.dry_run:
            args.append("--dry-run")

        log.debug(f"{self.banner}run: {shlex.join(args)}")
        if self.args.for_real:
            out = subprocess.check_output(args, text=True, env=env)
            data = json.loads(out)
            log.debug(data)

            # NOTE: `uv sync --script` doesn't respect environment variables.
            venv = Path(data.get("sync", {}).get("environment", {}).get("path", ""))
        else:  # dummy value
            venv = Path()

        log.info(f"{self.banner}uv sync")
        return venv

    # bundle

    def bundle_venv(self, bundle: ZipFile2, venv: Path) -> ZipFile2:
        """Bundle a `venv` into `bundle`."""
        pkgs = venv_site_packages(venv).parent
        for dirname, _, files in os.walk(pkgs):
            for f in files:
                if f in BUNDLE_EXCLUDE and ".dist-info" in str(dirname):
                    continue
                src = Path(dirname) / f
                rel = src.relative_to(pkgs)
                dest = "/".join(("Lib",) + rel.parts)
                add_path(bundle, src, dest, dry_run=self.args.dry_run)
        return bundle

    def bundle_entry_point(
        self,
        src: Path,
        dest: Path,
        *,
        entry_point: str,
        venv: Path | None = None,
    ) -> Path:
        """Return `Path` to the build entry point."""
        self.fs_copy(src, dest)
        with open_zip(dest, mode="a") as bundle:
            if venv:
                self.bundle_venv(bundle, venv)
            set_args(bundle, python_call(entry_point), dry_run=self.args.dry_run)

        log.info(f"bundled: {dest}")
        return dest

    def bundle_entry_points(
        self,
        pkg: str,
        version: str,
        venv: Path,
        cosmo_python: Path,
        output_dir: Path,
    ) -> dict[str, Path]:
        """Return mapping of entry point names to their bundle paths."""
        result: dict[str, Path] = {}

        venv = self.uv_sync(pkg=pkg, version=version, venv=venv)
        # have all deps built

        entry_points = console_scripts_from_venv(pkg, venv)
        if not self.args.entry:
            self.args.entry = list(entry_points.keys())

        for name in self.args.entry:
            if name not in entry_points:
                err = f"could not find entry point: '{name}'"
                err += "\n  tip: look at `[project.scripts]` in `pyproject.toml`"
                raise ValueError(err)
        # all entry points exist

        name = self.args.entry[0]
        first = self.bundle_entry_point(
            src=cosmo_python,
            dest=output_dir / name,
            venv=venv,
            entry_point=entry_points[name],
        )
        result[name] = first
        for name in self.args.entry[1:]:  # bundle rest by replacing .args
            result[name] = self.bundle_entry_point(
                first,
                output_dir / name,
                entry_point=entry_points[name],
            )
        # all entry points built
        return result

    def bundle_script(
        self,
        version: str,
        venv: Path | None,
        cosmo_python: Path,
        output_dir: Path | None,
        script: Path,
    ) -> Path:
        """Bundle an individual script."""
        if not script.is_file():
            raise FileNotFoundError(f"cannot find script file: {script}")

        dest = self.fs_copy(cosmo_python, (output_dir or script.parent) / script.stem)
        with open_zip(dest, mode="a") as bundle:
            self.bundle_venv(
                bundle,
                self.uv_sync(
                    pkg=script.name, version=version, venv=venv, script=script
                ),
            )
            add_path(bundle, script, script.name, dry_run=self.args.dry_run)
            set_args(bundle, script.name, dry_run=self.args.dry_run)

        log.info(f"bundled: {dest}")
        return script

    def run(self) -> None:
        """Build a venv and bundle it into a Cosmopolitan Python executable."""
        with tempfile.TemporaryDirectory(prefix="cosmofy-python-") as cosmo_temp:
            log.debug(f"temp dir={cosmo_temp}")
            cosmo_python = self.get_cosmo_python(Path(cosmo_temp) / "python")
            version = get_version(cosmo_python)
            if not version:
                raise ValueError("could not get Cosmopolitan Python version")
            # have cosmo python + version

            with tempfile.TemporaryDirectory(prefix="cosmofy-venv-") as venv_temp:
                log.debug(f"temp dir={venv_temp}")
                venv = Path(venv_temp)
                if self.args.entry or (not self.args.entry and not self.args.script):
                    if not self.args.output_dir:
                        self.args.output_dir = find_project_root() / "dist"
                    self.args.output_dir.mkdir(parents=True, exist_ok=True)
                    # have an output dir

                    pkg, pkg_ver = self.uv_version()
                    self.bundle_entry_points(
                        pkg=pkg,
                        version=version,
                        venv=venv,
                        cosmo_python=cosmo_python,
                        output_dir=self.args.output_dir,
                    )
                # all entry points built

                for script in self.args.script:
                    self.bundle_script(
                        version,
                        venv,
                        cosmo_python,
                        self.args.output_dir,
                        script,
                    )
                # all scripts built


def run(args: Args) -> int:
    """Main entry point for `cosmofy bundle`."""
    args.setup_logger()
    try:
        ensure_uv()
        Bundler(args).run()
    except Exception as e:
        args.show_error(log, e)
        return 2
    return 0


cmd = Command("cosmofy.bundle", Args, run)

if __name__ == "__main__":
    sys.exit(cmd.main())
