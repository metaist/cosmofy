"""Test bundler."""

# std
from pathlib import Path
import io

# pkg
from cosmofy.bundler import RE_MAIN
from cosmofy.bundler import _archive
from cosmofy.bundler import _pack_uint32
from cosmofy.bundler import compile_python
from cosmofy.zipfile2 import ZipFile2


def test_main_detector() -> None:
    """Detect __main__ blocks."""
    code = b"""if __name__ == "__main__":\n\t..."""
    assert RE_MAIN.search(code)

    code = b"""\nif __name__ == '__main__':\n\t..."""
    assert RE_MAIN.search(code)

    code = b"""\nif '__main__'  ==  __name__  :\n\t..."""
    assert RE_MAIN.search(code)

    code = b"""\n# if __name__ == "__main__":\n\t..."""
    assert not RE_MAIN.search(code)


def test_utilities() -> None:
    """Utility methods."""
    assert isinstance(_archive(io.BytesIO()), ZipFile2)
    assert isinstance(_pack_uint32(1024), bytes)

    src = Path(__file__).parent.parent / "src" / "cosmofy" / "__init__.py"
    assert isinstance(compile_python(src), bytearray)
    assert isinstance(compile_python(src, src.read_bytes()), bytearray)
