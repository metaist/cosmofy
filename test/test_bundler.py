"""Test bundler."""

# std
from pathlib import Path
import io
import os
import tempfile

# pkg
from cosmofy import bundler
from cosmofy.bundler import _archive
from cosmofy.bundler import _pack_uint32
from cosmofy.bundler import compile_python
from cosmofy.zipfile2 import ZipFile2

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_main_detector() -> None:
    """Detect __main__ blocks."""
    code = b"""if __name__ == "__main__":\n\t..."""
    assert bundler.RE_MAIN.search(code)

    code = b"""\nif __name__ == '__main__':\n\t..."""
    assert bundler.RE_MAIN.search(code)

    code = b"""\nif '__main__'  ==  __name__  :\n\t..."""
    assert bundler.RE_MAIN.search(code)

    code = b"""\n# if __name__ == "__main__":\n\t..."""
    assert not bundler.RE_MAIN.search(code)


def test_utilities() -> None:
    """Utility methods."""
    assert isinstance(_archive(io.BytesIO()), ZipFile2)
    assert isinstance(_pack_uint32(1024), bytes)

    src = Path(__file__).parent.parent / "src" / "cosmofy" / "__init__.py"
    assert isinstance(compile_python(src), bytearray)
    assert isinstance(compile_python(src, src.read_bytes()), bytearray)


def test_move() -> None:
    """Move and make executable."""
    content = b"test content"
    with tempfile.NamedTemporaryFile() as f:
        f.write(content)
        f.flush()

        with tempfile.NamedTemporaryFile() as g:
            src = Path(f.name)
            dest = Path(g.name)
            bundler.move_set_executable(src, dest)
            assert dest.read_bytes() == content
            assert os.access(dest, os.X_OK)


def test_globs() -> None:
    """Glob patterns."""

    src = EXAMPLES / "pkg-nested"
    assert list(bundler.expand_globs(src)) == []  # no patterns

    items = bundler.expand_globs(src, ".")
    assert next(items) == (src, {"__init__.py"})

    items = bundler.expand_globs(src, "..")
    assert next(items) == (src.parent, set())  # examples only has sub-folders

    items = list(bundler.expand_globs(src, "*"))
    assert items[0] == (src / "__init__.py", set())
    assert len(items) > 1

    # see same item multiple times
    items = list(bundler.expand_globs(src, "*", "*"))
    assert items

    src = EXAMPLES / "empty"
    src.mkdir(parents=True, exist_ok=True)
    assert list(bundler.expand_globs(src, "*")) == []
