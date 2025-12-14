# std
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterator

# pkg
from ..baton import arg
from ..args import GlobalArgs

fs_common_args = """\
  <bundle>                  Cosmopolitan file bundle
""".rstrip()


@dataclass
class FsCommonArgs(GlobalArgs):
    bundle: Path | None = arg(None, positional=True, required=True)
    """Cosmopolitan file bundle."""

    def ensure_bundle(self) -> bool:
        """Resolve `bundle` parameter and make sure it exists (in non-dry run)."""
        if self.bundle:
            self.bundle = self.bundle.resolve()

        if self.for_real and (self.bundle is None or not self.bundle.exists()):
            raise FileNotFoundError(f"Could not find Cosmopolitan file: {self.bundle}")

        return True


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
