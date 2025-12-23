"""Download files."""

# std
from datetime import datetime
from datetime import timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPResponse
from pathlib import Path
from typing import Iterator
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen
import hashlib
import logging
import shutil
import stat
import tempfile

# pkg
from . import DEFAULT_HASH
from . import COSMOFY_TIMEOUT

log = logging.getLogger(__name__)

CHUNK_SIZE = 65536
"""Default chunk size."""


def move_executable(src: Path, dest: Path) -> Path:
    """Set the executable bit and move a file."""
    mode = src.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    src.chmod(mode)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src, dest)
    log.debug(f"move: {src} to {dest}")
    return dest


def progress(response: HTTPResponse, prefix: str = "Downloading: ") -> Iterator[bytes]:
    """Display progress information."""
    header = response.getheader("Content-Length") or "0"
    total = int(header.strip())
    done = 0
    while chunk := response.read(CHUNK_SIZE):
        done += len(chunk)
        if total > 0:
            percent = done / total * 100
            print(f"\r{prefix}{percent:.2f}%", end="", flush=True)
        else:
            print(f"\r{prefix}{done} bytes", end="", flush=True)
        yield chunk
    print("")


def download(url: str, path: Path, timeout: int = COSMOFY_TIMEOUT) -> Path:
    """Download `url` to path."""
    log.info(f"download: {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=timeout) as response, path.open("wb") as output:
        for chunk in progress(response):
            output.write(chunk)
    return path


def download_if_newer(url: str, path: Path, timeout: int = COSMOFY_TIMEOUT) -> Path:
    """Download `url` to `path` if `url` is newer."""
    if not path.exists():
        return download(url, path)

    response = urlopen(Request(url, method="HEAD"), timeout=timeout)
    last_modified = response.headers.get("Last-Modified")
    if not last_modified:
        log.debug("no `Last-Modified` header; re-downloading")
        return download(url, path)

    try:
        local = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        remote = parsedate_to_datetime(last_modified)
        if remote > local:
            return download(url, path)
        return path  # cached version is current
    except (TypeError, ValueError):
        log.debug(f"could not parse `Last-Modified`: {last_modified}; re-downloading")
        return download(url, path)


def download_and_hash(
    url: str, path: Path, algo: str = DEFAULT_HASH, timeout: int = COSMOFY_TIMEOUT
) -> str:
    """Download `url` to `path` and return the hash."""
    log.info(f"download: {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.new(algo)
    with urlopen(url, timeout=timeout) as response, path.open("wb") as output:
        for chunk in progress(response):
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def download_release(
    url: str, path: Path, expected: str, algo: str = DEFAULT_HASH
) -> Path | None:
    """Download release from `url` checking the hash along the way."""
    log.info(f"download {url} to {path}")
    with tempfile.NamedTemporaryFile(delete=False) as out:
        temp = Path(out.name)
        try:
            received = download_and_hash(url, temp, algo)
        except HTTPError as e:
            log.error(f"{e}: {url}")
            return None

        if received != expected:
            log.error(f"hash mismatch: expected={expected}, received={received}")
            temp.unlink(missing_ok=True)
            return None

    log.debug(f"overwriting: {path}")
    return move_executable(temp, path)
