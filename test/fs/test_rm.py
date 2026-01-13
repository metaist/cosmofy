"""Test fs rm command."""

# std
from pathlib import Path
from shlex import split
import tempfile

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.fs.rm import Args
from cosmofy.fs.rm import remove_path
from cosmofy.fs.rm import run
from cosmofy.zipfile2 import ZipFile2


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip file1.txt file2.txt"))
    assert args.bundle == Path("bundle.zip")
    assert args.file == ["file1.txt", "file2.txt"]
    assert args.force is False
    assert args.recursive is False


def test_arg_parsing_flags() -> None:
    """Test flag parsing."""
    args = baton.parse(Args, split("bundle.zip -fr file.txt"))
    assert args.force is True
    assert args.recursive is True

    args = baton.parse(Args, split("bundle.zip --force --recursive file.txt"))
    assert args.force is True
    assert args.recursive is True


def test_remove_path_file() -> None:
    """Test removing a file."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "hello")
            z.writestr("other.txt", "world")

        with ZipFile2(path, "a") as z:
            remove_path(z, "test.txt")

        with ZipFile2(path, "r") as z:
            assert "test.txt" not in z.namelist()
            assert "other.txt" in z.namelist()
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_file_not_found() -> None:
    """Test removing a file that doesn't exist."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "hello")

        with ZipFile2(path, "a") as z:
            with pytest.raises(FileNotFoundError):
                remove_path(z, "nonexistent.txt")
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_file_not_found_force() -> None:
    """Test removing a nonexistent file with --force."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "hello")

        with ZipFile2(path, "a") as z:
            # Should not raise with force=True
            remove_path(z, "nonexistent.txt", force=True)
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_directory_no_recursive() -> None:
    """Test removing a directory without --recursive fails."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("dir/file.txt", "hello")

        with ZipFile2(path, "a") as z:
            with pytest.raises(Exception) as exc:
                remove_path(z, "dir/")
            assert "cannot remove directory" in str(exc.value)
            assert "--recursive" in str(exc.value)
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_directory_recursive() -> None:
    """Test removing a directory with --recursive."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("dir/", "")
            z.writestr("dir/file1.txt", "hello")
            z.writestr("dir/file2.txt", "world")
            z.writestr("other.txt", "keep")

        with ZipFile2(path, "a") as z:
            remove_path(z, "dir/", recursive=True)

        with ZipFile2(path, "r") as z:
            names = z.namelist()
            assert "dir/" not in names
            assert "dir/file1.txt" not in names
            assert "dir/file2.txt" not in names
            assert "other.txt" in names
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_dry_run() -> None:
    """Test removing with dry_run doesn't actually remove."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "hello")

        with ZipFile2(path, "a") as z:
            remove_path(z, "test.txt", dry_run=True)

        with ZipFile2(path, "r") as z:
            # File should still exist
            assert "test.txt" in z.namelist()
    finally:
        path.unlink(missing_ok=True)


def test_run_success() -> None:
    """Test run command success."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "hello")

        args = baton.parse(Args, split(f"{path} test.txt"))
        result = run(args)
        assert result == 0

        with ZipFile2(path, "r") as z:
            assert "test.txt" not in z.namelist()
    finally:
        path.unlink(missing_ok=True)


def test_run_file_not_found() -> None:
    """Test run command with nonexistent file returns error."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "hello")

        args = baton.parse(Args, split(f"{path} nonexistent.txt"))
        result = run(args)
        assert result == 2
    finally:
        path.unlink(missing_ok=True)


def test_run_glob_pattern() -> None:
    """Test run command with glob pattern."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("file1.txt", "1")
            z.writestr("file2.txt", "2")
            z.writestr("other.py", "3")

        args = baton.parse(Args, split(f"{path} '*.txt'"))
        result = run(args)
        assert result == 0

        with ZipFile2(path, "r") as z:
            names = z.namelist()
            assert "file1.txt" not in names
            assert "file2.txt" not in names
            assert "other.py" in names
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_directory_recursive_dry_run() -> None:
    """Test removing a directory with --recursive in dry_run mode."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("dir/", "")  # explicit directory entry
            z.writestr("dir/file.txt", "hello")

        with ZipFile2(path, "a") as z:
            remove_path(z, "dir/", recursive=True, dry_run=True)

        with ZipFile2(path, "r") as z:
            # Everything should still exist
            assert "dir/" in z.namelist()
            assert "dir/file.txt" in z.namelist()
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_directory_no_entry() -> None:
    """Test removing a directory that has no explicit entry (implicit dir)."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        # Create zip without explicit dir entry
        with ZipFile2(path, "w") as z:
            z.writestr("dir/file1.txt", "hello")
            z.writestr("dir/file2.txt", "world")
            # No "dir/" entry

        with ZipFile2(path, "a") as z:
            remove_path(z, "dir/", recursive=True)

        with ZipFile2(path, "r") as z:
            names = z.namelist()
            assert "dir/file1.txt" not in names
            assert "dir/file2.txt" not in names
    finally:
        path.unlink(missing_ok=True)


def test_remove_path_directory_with_results(tmp_path: Path) -> None:
    """Test removing a directory with results tracking."""
    bundle_path = tmp_path / "bundle.zip"

    with ZipFile2(bundle_path, "w") as z:
        z.writestr("dir/", "")  # explicit directory entry
        z.writestr("dir/file.txt", "hello")

    results: list[dict[str, object]] = []

    with ZipFile2(bundle_path, "a") as z:
        remove_path(z, "dir/", recursive=True, results=results)

    # Should have results for both file and directory
    assert len(results) == 2
    # Check directory entry in results
    dir_result = [r for r in results if r["is_dir"]]
    assert len(dir_result) == 1
    assert dir_result[0]["path"] == "dir/"


def test_run_json_output(tmp_path: Path) -> None:
    """Test run command with JSON output format."""
    import io
    import json
    import sys

    bundle_path = tmp_path / "bundle.zip"

    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "hello")

    args = baton.parse(Args, split(f"{bundle_path} --output-format json test.txt"))

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()
    try:
        result = run(args)
    finally:
        sys.stdout = old_stdout

    assert result == 0
    output = captured.getvalue()
    data = json.loads(output)
    assert "removed" in data
    assert any("test.txt" in item["path"] for item in data["removed"])
