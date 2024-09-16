"""Self-updater."""

# std
from datetime import datetime
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict
from typing import Optional
from urllib.request import Request
from urllib.request import urlopen
import hashlib
import logging
import re
import subprocess

log = logging.getLogger(__name__)

DEFAULT_HASH = "sha256"
"""Default hashing algorithm."""

CHUNK_SIZE = 65536
"""Default chunk size."""

RE_VERSION = re.compile(rb"\d+\.\d+\.\d+(-[\da-zA-Z-.]+)?(\+[\da-zA-Z-.]+)?")
"""Regex for a semver version string."""


def download(url: str, path: Path, chunk_size: int = CHUNK_SIZE) -> Path:
    """Download `url` to path."""
    log.info(f"Downloading {url} to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, path.open("wb") as output:
        while chunk := response.read(chunk_size):
            output.write(chunk)
    return path


def download_if_newer(url: str, path: Path, chunk_size: int = CHUNK_SIZE) -> Path:
    """Download `url` to `path` if `url` is newer."""
    exists = path.exists()
    need_download = not exists  # guess: exists => already downloaded
    if exists:
        local = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        response = urlopen(Request(url, method="HEAD"))
        remote = parsedate_to_datetime(response.headers.get("Last-Modified"))
        need_download = remote > local  # only download if newer
    return download(url, path, chunk_size) if need_download else path


def create_receipt(
    path: Path,
    algo: str = DEFAULT_HASH,
    date: Optional[datetime] = None,
    version: str = "",
) -> Dict[str, str]:
    """Create JSON receipt data."""
    digest = getattr(hashlib, algo)()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            digest.update(chunk)

    date = date or datetime.now()
    if not version:
        out = subprocess.run(
            f"{path} --version", shell=True, capture_output=True, check=True
        ).stdout
        if match := RE_VERSION.search(out):
            version = match.group().decode("utf-8")

    return {
        "algo": algo,
        "hash": digest.hexdigest(),
        "date": date.isoformat()[:19] + "Z",
        "version": version,
    }
