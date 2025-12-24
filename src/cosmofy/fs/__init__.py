# std
from fnmatch import translate
from typing import Iterator
import re


def shell_match(name: str, pat: str) -> bool:
    """Match following shell glob rules (* doesn't match /, ** matches anything)."""
    if name.startswith(".") and not pat.startswith("."):
        return False

    # Protect ** patterns with placeholders
    pat = pat.replace("**/", "\x00")  # **/ matches zero or more dirs
    pat = pat.replace("**", "\x01")  # ** at end matches anything
    regex = translate(pat)
    regex = regex.replace(".*", "[^/]*")  # `*` => doesn't match `/``
    regex = regex.replace("\x00", "(.*/)?")  # `**/` => 0+ path segments
    regex = regex.replace("\x01", ".*")  # `**` => anything
    return re.match(regex, name) is not None


def expand_glob(names: list[str], pat: str) -> Iterator[str]:
    """Return all file names that match the pattern."""
    if "*" in pat or "?" in pat:
        yield from (name for name in names if shell_match(name, pat))
    else:
        yield pat
