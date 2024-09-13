"""Test bundler."""

# std
from unittest.mock import patch
from pathlib import Path
import io
import os
import tempfile

# pkg
from cosmofy import bundler
from cosmofy.args import Args
from cosmofy.bundler import _archive
from cosmofy.bundler import _pack_uint32
from cosmofy.bundler import Bundler
from cosmofy.bundler import compile_python
from cosmofy.zipfile2 import ZipFile2

EXAMPLES = Path(__file__).parent.parent / "examples"
(EXAMPLES / "empty").mkdir(parents=True, exist_ok=True)  # cannot be committed


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


def test_copy() -> None:
    """Copy file."""
    content = b"test content"
    with tempfile.NamedTemporaryFile() as f, tempfile.NamedTemporaryFile() as g:
        f.write(content)
        f.flush()

        src, dest = Path(f.name), Path(g.name)
        Bundler(Args(dry_run=True, for_real=False)).fs_copy(src, dest)
        Bundler(Args()).fs_copy(src, dest)
        assert dest.read_bytes() == content


def test_move() -> None:
    """Move and make executable."""
    content = b"test content"
    with tempfile.NamedTemporaryFile() as f, tempfile.NamedTemporaryFile() as g:
        f.write(content)
        f.flush()

        src, dest = Path(f.name), Path(g.name)
        Bundler(Args(dry_run=True, for_real=False)).fs_move_executable(src, dest)
        Bundler(Args()).fs_move_executable(src, dest)
        assert dest.read_bytes() == content
        assert os.access(dest, os.X_OK)


def test_from_download() -> None:
    """Archive from cache/download."""
    test = Bundler(Args(dry_run=True, for_real=False))
    real = Bundler(Args())
    with tempfile.NamedTemporaryFile() as f, tempfile.NamedTemporaryFile() as g:
        src, dest = Path(f.name), Path(g.name)

        test.from_cache(src, dest)
        real.from_cache(src, dest)

        test.from_download(dest)
        real.from_download(dest)


def test_setup_temp() -> None:
    """Setup tempfile."""
    test = Bundler(Args(dry_run=True, for_real=False)).setup_temp()
    assert isinstance(test[0], Path)
    assert isinstance(test[1], ZipFile2)

    real = Bundler(Args()).setup_temp()
    assert isinstance(real[0], Path)
    assert real[1] is None  # gets built later
    real[0].unlink()  # cleanup


def test_setup_archive() -> None:
    """Setup archive."""
    # clone (dry run)
    assert Bundler(
        Args(dry_run=True, for_real=False, cosmo=True, clone=True)
    ).setup_archive()

    # cache (dry run)
    assert Bundler(Args(dry_run=True, for_real=False)).setup_archive()

    # fresh (dry run)
    assert Bundler(Args(dry_run=True, for_real=False, cache=None)).setup_archive()


def test_process() -> None:
    """Process a file."""
    test = Bundler(Args(dry_run=True, for_real=False))

    # find __main__ in file
    path = EXAMPLES / "pkg-with-init" / "__init__.py"
    out = test.process_file(path, ("pkg-with-init", "__init__"), tuple())
    assert out[0] == path.with_suffix(".pyc").name
    assert isinstance(out[1], bytearray)
    assert out[2] == ("pkg-with-init", "__init__")

    # find __main__ in package
    path = EXAMPLES / "pkg-with-main" / "__main__.py"
    out = test.process_file(path, ("pkg-with-main", "__main__"), tuple())
    assert out[0] == path.with_suffix(".pyc").name
    assert isinstance(out[1], bytearray)
    assert out[2] == ("pkg-with-main",)

    # non-.py file
    path = EXAMPLES / "pkg-with-main" / "py.typed"
    out = test.process_file(path, ("pkg-with-main", "py"), ("pkg-with-main",))
    assert out[0] == path.name
    assert out[1] == b""
    assert out[2] == ("pkg-with-main",)


def test_add() -> None:
    """Add files."""
    test = Bundler(Args(dry_run=True, for_real=False))
    real = Bundler(Args())
    archive = _archive(io.BytesIO())

    # empty directory
    path = EXAMPLES / "empty"
    include = [(path, set())]
    assert test.zip_add(archive, iter(include), {}) == ()

    # __init__.py without its parent
    path = EXAMPLES / "pkg-with-init" / "__init__.py"
    include = [(path, set())]
    assert test.zip_add(archive, iter(include), {}) == (path.parent.name, path.stem)
    assert real.zip_add(archive, iter(include), {}) == (path.parent.name, path.stem)

    # no main found
    path = EXAMPLES / "single-file" / "file-no-main.py"
    include = [(path, set())]
    assert test.zip_add(archive, iter(include), {}) == (path.stem,)

    # include + exclude
    path = EXAMPLES / "pkg-nested"
    include = bundler.expand_globs(EXAMPLES, path.name)
    exclude = {path / "sub-folder" / "ignore.py"}
    assert test.zip_add(archive, include, exclude) == ("pkg-nested", "sub-folder")


def test_remove() -> None:
    """Remove files."""
    test = Bundler(Args(dry_run=True, for_real=False))
    real = Bundler(Args())
    with tempfile.NamedTemporaryFile() as f:
        archive = _archive(f.name)
        archive.add_file(".args", "-m FAKE")
        test.zip_remove(archive, ".args")
        real.zip_remove(archive, ".args")


def test_write_args() -> None:
    """Write .args."""
    test = Bundler(Args(dry_run=True, for_real=False))
    archive = _archive(io.BytesIO())
    assert test.write_args(archive, tuple())  # skip writing
    assert test.write_args(archive, ("foo", "__init__"))

    real = Bundler(Args(args="-m foo.bar --extra"))
    assert real.write_args(archive, ("foo", "bar"))


def test_write_output() -> None:
    """Write output zip."""
    test = Bundler(Args(dry_run=True, for_real=False))
    with tempfile.NamedTemporaryFile() as f:
        assert test.write_output(_archive(f), tuple()) == Path("out.com")

    archive = _archive(io.BytesIO())
    assert test.write_output(archive, ("foo", "__init__")) == Path("foo.com")
    assert test.write_output(archive, ("foo", "bar")) == Path("bar.com")


def test_run() -> None:
    """Run bundler."""
    test = Bundler(Args(dry_run=True, for_real=False))
    assert test.run() == Path("out.com")
