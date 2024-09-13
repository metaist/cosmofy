"""Self-updater."""

# std
from datetime import datetime
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request
from urllib.request import urlopen
import logging

log = logging.getLogger(__name__)

CHUNK_SIZE = 65536
"""Default chunk size."""


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
    need_download = not path.exists()  # guess: exists => already downloaded
    if path.exists():
        local = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        response = urlopen(Request(url, method="HEAD"))
        remote = parsedate_to_datetime(response.headers.get("Last-Modified"))
        need_download = remote > local  # only download if newer
    return download(url, path, chunk_size) if need_download else path
