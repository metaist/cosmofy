# std
from dataclasses import dataclass
from pathlib import Path

# pkg
from ..args import Arg
from ..args import store
from ..args import GlobalArgs

fs_common_args = """\
  <bundle>                  Cosmopolitan file bundle
""".rstrip()

fs_common_arglist: list[Arg] = [Arg("bundle", kind=Path, action=store, required=True)]


@dataclass
class FsCommonArgs(GlobalArgs):
    bundle: Path | None = None
    """Cosmopolitan file bundle."""

    def ensure_bundle(self) -> bool:
        """Resolve `bundle` parameter and make sure it exists (in non-dry run)."""
        if self.bundle:
            self.bundle = self.bundle.resolve()

        if self.for_real and (self.bundle is None or not self.bundle.exists()):
            raise FileNotFoundError(f"Could not find Cosmopolitan file: {self.bundle}")

        return True
