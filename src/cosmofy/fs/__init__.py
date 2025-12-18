# std
from fnmatch import fnmatchcase
from typing import Iterator


def shell_match(name: str, pat: str) -> bool:
    """Match following weird starts-with-dot rules."""
    if name.startswith(".") and not pat.startswith("."):
        return False
    return fnmatchcase(name, pat)


def expand_glob(names: list[str], pat: str) -> Iterator[str]:
    """Return all file names that match the pattern."""
    if "*" in pat or "?" in pat:
        yield from (name for name in names if shell_match(name, pat))
    else:
        yield pat
