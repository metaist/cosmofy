"""Test fs add command."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import patch
import os
import tempfile

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.fs.add import add_data
from cosmofy.fs.add import add_path
from cosmofy.fs.add import Args
from cosmofy.fs.add import run
from cosmofy.zipfile2 import ZipFile2


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip file1.txt file2.txt"))
    assert args.bundle == Path("bundle.zip")
    assert args.file == ["file1.txt", "file2.txt"]
    assert args.force is False
    assert args.compile_bytecode is False


def test_arg_parsing_flags() -> None:
    """Test flag parsing."""
    args = baton.parse(Args, split("bundle.zip -fc file.txt"))
    assert args.force is True
    assert args.compile_bytecode is True


def test_arg_parsing_dest() -> None:
    """Test --dest option parsing."""
    args = baton.parse(Args, split("bundle.zip --dest Lib/site-packages file.txt"))
    assert args.dest == "Lib/site-packages"


def test_arg_parsing_chdir() -> None:
    """Test --chdir option parsing."""
    args = baton.parse(Args, split("bundle.zip --chdir /tmp file.txt"))
    assert args.chdir == Path("/tmp")


def test_add_data_string() -> None:
    """Test adding string data."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            pass  # create empty

        with ZipFile2(path, "a") as z:
            add_data(z, "hello world", "test.txt")

        with ZipFile2(path, "r") as z:
            assert z.read("test.txt") == b"hello world"
    finally:
        path.unlink(missing_ok=True)


def test_add_data_bytes() -> None:
    """Test adding bytes data."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            pass

        with ZipFile2(path, "a") as z:
            add_data(z, b"\x00\x01\x02", "binary.bin")

        with ZipFile2(path, "r") as z:
            assert z.read("binary.bin") == b"\x00\x01\x02"
    finally:
        path.unlink(missing_ok=True)


def test_add_data_exists_no_force() -> None:
    """Test adding data when file exists without --force."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "original")

        with ZipFile2(path, "a") as z:
            with pytest.raises(FileExistsError) as exc:
                add_data(z, "new", "test.txt")
            assert "already exists" in str(exc.value)
            assert "--force" in str(exc.value)
    finally:
        path.unlink(missing_ok=True)


def test_add_data_exists_with_force() -> None:
    """Test adding data when file exists with --force."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "original")

        with ZipFile2(path, "a") as z:
            add_data(z, "new content", "test.txt", force=True)

        with ZipFile2(path, "r") as z:
            assert z.read("test.txt") == b"new content"
    finally:
        path.unlink(missing_ok=True)


def test_add_data_dry_run() -> None:
    """Test adding data with dry_run doesn't actually add."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            pass

        with ZipFile2(path, "a") as z:
            add_data(z, "hello", "test.txt", dry_run=True)

        with ZipFile2(path, "r") as z:
            assert "test.txt" not in z.namelist()
    finally:
        path.unlink(missing_ok=True)


def test_add_path_file(tmp_path: Path) -> None:
    """Test adding a file from filesystem."""
    src = tmp_path / "source.txt"
    src.write_text("file content")

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    with ZipFile2(bundle_path, "a") as z:
        add_path(z, src, "dest.txt")

    with ZipFile2(bundle_path, "r") as z:
        assert z.read("dest.txt") == b"file content"


def test_add_path_directory(tmp_path: Path) -> None:
    """Test adding a directory recursively."""
    subdir = tmp_path / "mydir"
    subdir.mkdir()
    (subdir / "file1.txt").write_text("one")
    (subdir / "file2.txt").write_text("two")

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    with ZipFile2(bundle_path, "a") as z:
        add_path(z, subdir, "pkg")

    with ZipFile2(bundle_path, "r") as z:
        assert z.read("pkg/file1.txt") == b"one"
        assert z.read("pkg/file2.txt") == b"two"


def test_add_path_not_found(tmp_path: Path) -> None:
    """Test adding a nonexistent path."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    with ZipFile2(bundle_path, "a") as z:
        with pytest.raises(FileNotFoundError):
            add_path(z, tmp_path / "nonexistent", "dest")


def test_add_path_compile_bytecode(tmp_path: Path) -> None:
    """Test adding with --compile-bytecode."""
    src = tmp_path / "script.py"
    src.write_text("print('hello')")

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    with patch("cosmofy.fs.add.compile_python_external") as mock_compile:
        mock_compile.return_value = b"\x00\x01\x02\x03"
        python_path = tmp_path / "python"

        with ZipFile2(bundle_path, "a") as z:
            add_path(z, src, "script.py", compile_bytecode=True, python=python_path)

        mock_compile.assert_called_once()

    with ZipFile2(bundle_path, "r") as z:
        # Should have .pyc, not .py
        assert "script.pyc" in z.namelist()
        assert "script.py" not in z.namelist()


def test_add_path_circular_symlink(tmp_path: Path) -> None:
    """Test handling of circular symlinks."""
    # Create a circular symlink
    link = tmp_path / "link"
    os.symlink(tmp_path, link)

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    with ZipFile2(bundle_path, "a") as z:
        # Should handle circular symlink gracefully
        add_path(z, tmp_path, "pkg")


def test_run_success(tmp_path: Path) -> None:
    """Test run command success."""
    src = tmp_path / "file.txt"
    src.write_text("content")

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    args = baton.parse(Args, split(f"{bundle_path} --chdir {tmp_path} file.txt"))
    result = run(args)
    assert result == 0

    with ZipFile2(bundle_path, "r") as z:
        assert "file.txt" in z.namelist()


def test_run_with_dest(tmp_path: Path) -> None:
    """Test run command with --dest prefix."""
    src = tmp_path / "file.txt"
    src.write_text("content")

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    args = baton.parse(
        Args, split(f"{bundle_path} --dest Lib --chdir {tmp_path} file.txt")
    )
    result = run(args)
    assert result == 0

    with ZipFile2(bundle_path, "r") as z:
        assert "Lib/file.txt" in z.namelist()


def test_run_file_not_found(tmp_path: Path) -> None:
    """Test run command with nonexistent file returns error."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w"):
        pass

    args = baton.parse(Args, split(f"{bundle_path} nonexistent.txt"))
    result = run(args)
    assert result == 2


def test_add_path_compile_bytecode_dry_run(tmp_path: Path) -> None:
    """Test adding with --compile-bytecode in dry_run mode."""
    src = tmp_path / "script.py"
    src.write_text("print('hello')")

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    python_path = tmp_path / "python"

    with ZipFile2(bundle_path, "a") as z:
        # dry_run=True should skip compile_python_external call
        add_path(
            z, src, "script.py", compile_bytecode=True, python=python_path, dry_run=True
        )

    with ZipFile2(bundle_path, "r") as z:
        # Nothing should be added in dry run
        assert "script.pyc" not in z.namelist()
        assert "script.py" not in z.namelist()


def test_run_file_outside_chdir(tmp_path: Path) -> None:
    """Test run command with file path outside chdir directory."""
    # Create a file in a different location than chdir
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    src = other_dir / "file.txt"
    src.write_text("content")

    chdir = tmp_path / "work"
    chdir.mkdir()

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    # Use absolute path to file outside chdir
    args = baton.parse(Args, split(f"{bundle_path} --chdir {chdir} {src}"))
    result = run(args)
    assert result == 0

    with ZipFile2(bundle_path, "r") as z:
        # File should be added with path as-is (relative path handling)
        names = z.namelist()
        assert any("file.txt" in n for n in names)
