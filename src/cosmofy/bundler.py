"""Cosmofy bundler."""

# std
from __future__ import annotations
from importlib.util import MAGIC_NUMBER
from pathlib import Path
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union
import io
import logging
import marshal
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile

# pkg
from .args import Args
from .args import COSMOFY_PYTHON_URL
from .updater import download
from .updater import download_if_newer
from .zipfile2 import ZipFile2

log = logging.getLogger(__name__)

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


def _archive(path: Union[str, Path, io.BytesIO]) -> ZipFile2:
    return ZipFile2(path, mode="a", compression=zipfile.ZIP_DEFLATED, compresslevel=9)


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


def move_set_executable(src: Path, dest: Path) -> Path:
    """Move a file and set its executable bit."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src, dest)
    mode = dest.stat().st_mode | stat.S_IEXEC
    dest.chmod(mode)
    return dest


def expand_globs(start: Path, *patterns: str) -> Iterator[Tuple[Path, Set[str]]]:
    """Yield paths of all glob patterns."""
    seen: Set[Path] = set()
    for pattern in patterns:
        for path in sorted(start.glob(pattern)):
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
        self.archive = self.setup_archive()

    def archive_from_clone(
        self, dest: Path, archive: Optional[ZipFile2] = None
    ) -> ZipFile2:
        """Clone the archive from `sys.executable`."""
        log.debug(f"{self.banner}copy: {sys.executable} to {dest}")
        if self.args.for_real:
            shutil.copy(sys.executable, dest)

        log.debug(f"{self.banner}remove: cosmofy")
        archive = archive or _archive(dest)
        if self.args.for_real:
            archive.remove(".args")
            archive.remove("Lib/site-packages/cosmofy/*")
        return archive

    def archive_from_cache(
        self, dest: Path, archive: Optional[ZipFile2] = None
    ) -> ZipFile2:
        """Copy the archive from cache."""
        assert self.args.cache

        log.debug(f"{self.banner}download (if newer): {COSMOFY_PYTHON_URL}")
        if self.args.for_real:
            download_if_newer(COSMOFY_PYTHON_URL, self.args.cache / "python")

        log.debug(f"{self.banner}copy: {self.args.cache / "python"} to {dest}")
        if self.args.for_real:
            shutil.copy(self.args.cache / "python", dest)

        return archive or _archive(dest)

    def archive_from_download(
        self, dest: Path, archive: Optional[ZipFile2] = None
    ) -> ZipFile2:
        """Download archive."""
        log.debug(f"{self.banner}download (fresh): {COSMOFY_PYTHON_URL} to {dest}")
        if self.args.for_real:
            download(COSMOFY_PYTHON_URL, dest)
        return archive or _archive(dest)

    def setup_archive(self) -> ZipFile2:
        """Clone, copy from cache, or download the archive."""
        archive = None
        if self.args.for_real:
            temp = Path(tempfile.NamedTemporaryFile(delete=False).name)
        else:
            temp = Path(tempfile.gettempprefix()) / "DRY-RUN"
            archive = _archive(io.BytesIO())

        if self.args.clone:
            archive = self.archive_from_clone(temp, archive)
        elif self.args.cache:
            archive = self.archive_from_cache(temp, archive)
        else:
            archive = self.archive_from_download(temp, archive)
        return archive

    def add_files(
        self, include: Iterator[Tuple[Path, Set[str]]], exclude: Set[Path]
    ) -> Tuple[str, ...]:
        modules: Dict[Path, Tuple[str, ...]] = {}
        main_module: Tuple[str, ...] = tuple()
        pkgs = ("Lib", "site-packages")
        for path, files in include:
            if path in exclude:
                continue
            if path.is_dir():
                if any(True for p in PACKAGE_FILES if p in files):
                    modules[path] = modules.get(path.parent, tuple()) + (path.name,)
                continue
            # path is a file

            data = path.read_bytes()
            file_name = path.name
            parent_module = modules.get(path.parent, tuple())
            modules[path] = parent_module + (path.stem,)

            if not main_module and file_name in MAIN_FILES:
                main_module = modules[path][:-1]
                log.debug(f"found main: {main_module}")

            if path.suffix == ".py":  # can read or compile .pyc
                if not main_module and RE_MAIN.search(data):
                    main_module = modules[path]
                    log.debug(f"found main: {main_module}")
                data = compile_python(path, data)
                file_name = path.with_suffix(".pyc").name  # change name

            # ready to add
            dest = "/".join(pkgs + parent_module + (file_name,))
            log.info(f"{self.banner}add: {dest}")
            if self.args.for_real:
                self.archive.add_file(dest, data, 0o644)

        return main_module or next(iter(modules.values()))

    def remove_files(self, patterns: List[str]) -> Bundler:
        """Remove glob patterns from the archive."""
        for_real = not self.args.dry_run
        for pattern in patterns:
            log.info(f"{self.banner}remove: {pattern}")
            if for_real:
                self.archive.remove(pattern)
        return self

    def run(self) -> Path:
        """Run the bundler."""
        args = self.args
        archive = self.archive

        include = expand_globs(Path.cwd(), *args.add)
        exclude = set(p[0] for p in expand_globs(Path.cwd(), *args.exclude))
        main_module = self.add_files(include, exclude)
        self.remove_files(args.remove)
        # files added & removed

        python_args = args.args or f"-m {'.'.join(main_module)}"
        log.debug(f"{self.banner}.args = {python_args}")
        if self.args.for_real:
            archive.add_file(".args", python_args.replace(" ", "\n"), 0o644)
        # .args written

        if main_module[-1] == "__init__":
            main_module = main_module[:-1]
        output = args.output or Path(f"{main_module[-1]}.com")

        log.debug(f"{self.banner}move and chmod +x: {output}")
        if self.args.for_real and archive.filename:
            move_set_executable(Path(archive.filename), output)

        log.info(f"{self.banner}bundled: {output}")
        return output
