# std
from fnmatch import translate
from typing import Iterator
import re


def shell_match(name: str, pat: str) -> bool:
    """Match following shell glob rules.
    - `*` doesn't match `/` or leading dot
    - `**` matches anything
    """
    if name.startswith(".") and not pat.startswith("."):
        return False

    # Protect ** patterns with placeholders
    pat = pat.replace("**/", "\x00")
    pat = pat.replace("**", "\x01")
    regex = translate(pat)
    # * should not match /
    regex = regex.replace(".*", "[^/]*")
    # * after / should not match leading dot (hidden files)
    regex = regex.replace("/[^/]*", "/(?![.])[^/]*")
    # **/ matches zero or more non-hidden directories
    regex = regex.replace("\x00", "((?![.])[^/]*/)*")
    # ** at end matches anything
    regex = regex.replace("\x01", ".*")
    return re.match(regex, name) is not None


def expand_glob(names: list[str], pat: str) -> Iterator[str]:
    """Resolve a file pattern.

    Glob patterns are matched against `names`. Literal paths are passed
    through unchanged (caller is responsible for checking existence).
    """
    if "*" in pat or "?" in pat:
        yield from (name for name in names if shell_match(name, pat))
    else:
        yield pat
