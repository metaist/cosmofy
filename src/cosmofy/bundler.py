"""Cosmofy bundler."""

# std
from __future__ import annotations
from pathlib import Path
from shlex import split
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union
import io
import logging
import os
import shlex
import shutil
import sys
import tempfile
import zipfile

# pkg
from .args import Args
from .downloader import download
from .downloader import download_if_newer
from .downloader import move_executable
from .pythonoid import compile_python
from .pythonoid import MAIN_FILES
from .pythonoid import PACKAGE_FILES
from .pythonoid import Pkg
from .pythonoid import PythonArgs
from .pythonoid import RE_MAIN
from .receipt import Receipt
from .updater import PATH_COSMOFY
from .updater import PATH_RECEIPT
from .zipfile2 import ZipFile2

log = logging.getLogger(__name__)


def _archive(path: Union[str, Path, io.BytesIO]) -> ZipFile2:
    return ZipFile2(path, mode="a", compression=zipfile.ZIP_DEFLATED, compresslevel=9)


def expand_globs(start: Path, *patterns: str) -> Iterator[Tuple[Path, Set[str]]]:
    """Yield paths of all glob patterns."""
    seen: Set[Path] = set()
    for pattern in patterns:
        if pattern == ".":
            paths = [start]
        elif pattern == "..":
            paths = [start.parent]
        else:
            paths = sorted(start.glob(pattern))

        for path in paths:
            if not path.is_dir():
                if path not in seen:
                    seen.add(path)
                    yield (path, set())
                continue

            for dirname, _, files in os.walk(path):
                folder = Path(dirname)
                if folder not in seen:
                    seen.add(folder)
                    yield (folder, set(files))

                for name in sorted(files):
                    file = folder / name
                    if file not in seen:
                        seen.add(file)
                        yield (file, set())


class Bundler:
    """Wrapper around the bundling process."""

    args: Args
    """Parse command-line arguments."""

    archive: ZipFile2
    """Cosmopolitan APE file."""

    banner: str
    """Log prefix for dry-runs."""

    def __init__(self, args: Args):
        """Construct a bundler."""
        self.args = args
        self.banner = "[DRY RUN] " if args.dry_run else ""

    def fs_copy(self, src: Path, dest: Path) -> Path:
        """Copy a file from `src` to `dest`."""
        log.debug(f"{self.banner}copy: {src} to {dest}")
        if self.args.for_real:
            shutil.copy(src, dest)
        return dest

    def fs_move_executable(self, src: Path, dest: Path) -> Path:
        """Move a file and set its executable bit."""
        log.debug(f"{self.banner}move executable: {src} to {dest}")
        if self.args.for_real:
            move_executable(src, dest)
        return dest

    def from_cache(
        self, src: Path, dest: Path, archive: Optional[ZipFile2] = None
    ) -> ZipFile2:
        """Copy the archive from cache."""
        log.debug(f"{self.banner}download (if newer): {self.args.python_url}")
        if self.args.for_real:
            download_if_newer(self.args.python_url, src)

        self.fs_copy(src, dest)
        return archive or _archive(dest)

    def from_download(self, dest: Path, archive: Optional[ZipFile2] = None) -> ZipFile2:
        """Download archive."""
        log.debug(f"{self.banner}download (fresh): {self.args.python_url} to {dest}")
        if self.args.for_real:
            download(self.args.python_url, dest)
        return archive or _archive(dest)

    def setup_temp(self) -> Tuple[Path, Optional[ZipFile2]]:
        """Setup a temporary file and construct a ZipFile (if non-dry-run)."""
        archive = None
        if self.args.for_real:
            temp = Path(tempfile.NamedTemporaryFile(delete=False).name)
        else:
            temp = Path(tempfile.gettempprefix()) / "DRY-RUN"
            archive = _archive(io.BytesIO())
        return temp, archive

    def setup_archive(self) -> ZipFile2:
        """Clone, copy from cache, or download the archive."""
        temp, archive = self.setup_temp()
        if self.args.clone:
            paths = [".args", f"{PATH_COSMOFY}/*"]
            self.fs_copy(Path(sys.executable), temp)
            archive = self.zip_remove(archive or _archive(temp), *paths)
        elif self.args.cache:
            archive = self.from_cache(self.args.cache / "python", temp, archive)
        else:
            archive = self.from_download(temp, archive)
        return archive

    def process_file(
        self, path: Path, module: Pkg, main: Pkg
    ) -> Tuple[str, Union[bytes, bytearray], Pkg]:
        """Search for main module and compile `.py` files."""
        name, data = path.name, path.read_bytes()
        if not main and name in MAIN_FILES:
            main = module[:-1]
            log.debug(f"found main: {main}")

        # NOTE: We only work on .py files because .pyc files are not searchable.
        if path.suffix == ".py":
            if not main and RE_MAIN.search(data):
                main = module
                log.debug(f"found main: {main}")
            name = path.with_suffix(".pyc").name  # change name
            data = compile_python(path, data)
        return name, data, main

    def zip_add(
        self,
        archive: ZipFile2,
        include: Iterator[Tuple[Path, Set[str]]],
        exclude: Set[Path],
    ) -> Pkg:
        """Add files to `archive` while searching for `main` entry point."""
        modules: Dict[Path, Pkg] = {}
        main: Pkg = tuple()
        pkgs = ("Lib", "site-packages")
        for path, files in include:
            if path in exclude:
                log.debug(f"{self.banner}exclude: {path}")
                continue
            if path.is_dir():
                if any(True for p in PACKAGE_FILES if p in files):
                    modules[path] = modules.get(path.parent, tuple()) + (path.name,)
                continue
            # path is a file

            parent = modules.get(path.parent, tuple())
            if not parent and path.name in PACKAGE_FILES:
                parent = (path.parent.name,)
            modules[path] = module = parent + (path.stem,)

            name, data, main = self.process_file(path, module, main)
            dest = "/".join(pkgs + parent + (name,))
            log.info(f"{self.banner}add: {dest}")
            if self.args.for_real:
                archive.add_file(dest, data, 0o644)

        if not main and modules.values():
            main = next(iter(modules.values()))
        return main

    def zip_remove(self, archive: ZipFile2, *patterns: str) -> ZipFile2:
        """Remove glob patterns from the archive."""
        for pattern in patterns:
            log.info(f"{self.banner}remove: {pattern}")
            if self.args.for_real:
                archive.remove(pattern)
        return archive

    def add_updater(self, archive: ZipFile2, python_args: str, receipt: Receipt) -> str:
        """Add `cosmofy.updater` and `receipt` to `archive`."""
        try:
            PythonArgs.parse(split(python_args))  # we can handle these args
            python_args = f"-m cosmofy.updater {python_args}".strip()
        except ValueError as e:
            log.error(f"Cannot add updater: {e}")
            sys.exit(1)

        assert receipt.is_valid()
        data: Union[str, bytes, bytearray]

        dest = PATH_RECEIPT
        data = str(receipt)
        log.debug(f"{self.banner} local receipt: {data}")
        log.info(f"{self.banner}add: {dest}")
        if self.args.for_real:
            archive.add_file(dest, data, 0o644)

        files = ["downloader.py", "pythonoid.py", "receipt.py", "updater.py"]
        for file in files:
            dest = f"{PATH_COSMOFY}/{file}c"
            if archive.NameToInfo.get(dest):  # already done
                log.debug(f"{self.banner}already exists: {dest}")
                continue

            if self.args.cosmo:  # clone from self
                log.debug(f"{self.banner}clone from: {sys.executable}")
                bundle = ZipFile2(sys.executable, "r")
                data = bundle.read(dest)
            else:
                path = Path(__file__).parent / file
                log.debug(f"{self.banner}compile from: {path}")
                data = compile_python(path)

            log.info(f"{self.banner}add: {dest}")
            if self.args.for_real:
                archive.add_file(dest, data, 0o644)

        return python_args

    def write_args(self, archive: ZipFile2, main: Pkg) -> Receipt:
        """Write special .args file."""
        receipt = Receipt(
            receipt_url=self.args.receipt_url,
            release_url=self.args.release_url,
        )
        python_args = ""
        if self.args.args or main:
            python_args = self.args.args or f"-m {'.'.join(main)}"
        if self.args.add_updater:  # embedded receipt
            python_args = self.add_updater(archive, python_args, receipt)

        if python_args:
            log.debug(f"{self.banner}.args = {python_args}")
            if self.args.for_real:
                archive.add_file(".args", "\n".join(shlex.split(python_args)), 0o644)
        return receipt

    def write_output(self, archive: ZipFile2, main: Pkg) -> Path:
        """Move output to appropriate place."""
        if not main:
            main = ("out",)
        elif main[-1] == "__init__":
            main = main[:-1]

        output = self.args.output or Path(f"{main[-1]}.com")
        if archive.filename:
            self.fs_move_executable(Path(archive.filename), output)
        log.info(f"{self.banner}created: {output}")
        return output

    def write_receipt(self, bundle: Path, receipt: Receipt) -> Receipt:
        """Write published receipt."""
        receipt.update_from(
            Receipt.from_path(bundle, self.args.release_version),
            "algo",
            "hash",
            "version",
            kind="published",
        )
        assert receipt.is_valid()

        data = str(receipt)
        log.debug(f"{self.banner} remote receipt: {data}")

        output = self.args.receipt or bundle.with_suffix(f"{bundle.suffix}.json")
        log.info(f"{self.banner}write: {output}")
        if self.args.for_real:
            output.write_text(data)
        return receipt

    def run(self) -> Path:
        """Run the bundler."""
        archive = self.setup_archive()
        include = expand_globs(Path.cwd(), *self.args.add)
        exclude = set(p[0] for p in expand_globs(Path.cwd(), *self.args.exclude))
        main = self.zip_add(archive, include, exclude)
        self.zip_remove(archive, *self.args.remove)
        receipt = self.write_args(archive, main)
        archive.close()  # release the file

        output = self.write_output(archive, main)
        if self.args.add_updater:  # published receipt
            receipt = self.write_receipt(output, receipt)
        return output
