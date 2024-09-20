"""Download files."""

# std
from datetime import datetime
from datetime import timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPResponse
from pathlib import Path
from typing import Iterator
from typing import Optional
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen
import hashlib
import logging
import shutil
import stat
import tempfile

# pkg
from .receipt import DEFAULT_HASH
from .receipt import Receipt

log = logging.getLogger(__name__)

CHUNK_SIZE = 65536
"""Default chunk size."""


def move_executable(src: Path, dest: Path) -> Path:
    """Set the executable bit and move a file."""
    mode = src.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    src.chmod(mode)

    dest.parent.mkdir(parents=True, exist_ok=True)
    # TODO 2024-10-31 @ py3.8 EOL: use `Path` instead of `str`
    shutil.move(str(src), str(dest))
    return dest


def progress(response: HTTPResponse, prefix: str = "Downloading: ") -> Iterator[bytes]:
    """Display progress information."""
    header = response.getheader("Content-Length") or "0"
    total = int(header.strip())
    done = 0
    while chunk := response.read(CHUNK_SIZE):
        done += len(chunk)
        percent = done / total * 100
        print(f"\r{prefix}{percent:.2f}%", end="", flush=True)
        yield chunk
    print("")


def download(url: str, path: Path) -> Path:
    """Download `url` to path."""
    log.info(f"Download {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, path.open("wb") as output:
        for chunk in progress(response):
            output.write(chunk)
    return path


def download_if_newer(url: str, path: Path) -> Path:
    """Download `url` to `path` if `url` is newer."""
    exists = path.exists()
    need_download = not exists  # guess: exists => already downloaded
    if exists:
        local = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        response = urlopen(Request(url, method="HEAD"))
        remote = parsedate_to_datetime(response.headers.get("Last-Modified"))
        need_download = remote > local  # only download if newer
    return download(url, path) if need_download else path


def download_and_hash(url: str, path: Path, algo: str = DEFAULT_HASH) -> str:
    """Download `url` to `path` and return the hash."""
    log.info(f"Download {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.new(algo)
    with urlopen(url) as response, path.open("wb") as output:
        for chunk in progress(response):
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def download_receipt(url: str) -> Optional[Receipt]:
    """Try to download a receipt."""
    log.info(f"Download: {url}")
    receipt = None
    try:
        receipt = Receipt.from_url(url)
    except HTTPError as e:
        log.error(f"{e}: {url}")
    return receipt


def download_release(
    url: str, path: Path, expected: str, algo: str = DEFAULT_HASH
) -> Optional[Path]:
    """Download release from `url` checking the hash along the way."""
    log.info(f"Download {url} to {path}")
    with tempfile.NamedTemporaryFile(delete=False) as out:
        temp = Path(out.name)
        try:
            received = download_and_hash(url, temp, algo)
        except HTTPError as e:
            log.error(f"{e}: {url}")
            return None

        if received != expected:
            log.error(f"Hash mismatch: expected={expected}, received={received}")
            temp.unlink(missing_ok=True)
            return None

    log.debug(f"Overwriting: {path}")
    return move_executable(temp, path)
