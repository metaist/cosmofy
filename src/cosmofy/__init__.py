"""cosmofy: Cosmopolitan Python Bundler"""

# std
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

try:
    __version__ = version("cosmofy")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__pubdate__ = "2025-12-24T03:14:02Z"
