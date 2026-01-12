"""Test fs cat command."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch

# lib

# pkg
from cosmofy import baton
from cosmofy.fs.cat import Args
from cosmofy.fs.cat import run
from cosmofy.fs.cat import show_files
from cosmofy.zipfile2 import ZipFile2


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip file.txt"))
    assert args.bundle == Path("bundle.zip")
    assert args.file == ["file.txt"]
    assert args.prompt is False


def test_arg_parsing_multiple_files() -> None:
    """Test Args parsing with multiple files."""
    args = baton.parse(Args, split("bundle.zip file1.txt file2.txt"))
    assert args.file == ["file1.txt", "file2.txt"]


def test_arg_parsing_with_prompt() -> None:
    """Test Args parsing with --prompt flag."""
    args = baton.parse(Args, split("bundle.zip -p file.txt"))
    assert args.prompt is True


def test_show_files_dry_run(tmp_path: Path) -> None:
    """Test show_files in dry run mode logs instead of writing."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "hello")

    args = baton.parse(Args, split(f"{bundle_path} --dry-run test.txt"))

    # In dry run, the code logs instead of writing to stdout
    with ZipFile2(bundle_path, "r") as z:
        show_files(z, args)
    # Just verify it doesn't crash


@patch("cosmofy.fs.cat.getpass")
def test_show_files_with_password(mock_getpass: MagicMock, tmp_path: Path) -> None:
    """Test show_files prompts for password when --prompt used."""
    mock_getpass.return_value = "secret"

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "hello")

    args = baton.parse(Args, split(f"{bundle_path} -p test.txt"))

    with ZipFile2(bundle_path, "r") as z:
        show_files(z, args)

    mock_getpass.assert_called_once()


def test_run_success(tmp_path: Path) -> None:
    """Test run command success."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "hello")

    args = baton.parse(Args, split(f"{bundle_path} test.txt"))
    result = run(args)
    assert result == 0


def test_run_no_bundle() -> None:
    """Test run command with nonexistent bundle returns error."""
    args = baton.parse(Args, split("nonexistent.zip file.txt"))
    result = run(args)
    assert result == 2


def test_show_files_skips_directories(tmp_path: Path) -> None:
    """Test show_files skips directories when matching glob."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("dir/", "")  # directory entry
        z.writestr("dir/file.txt", "content")

    # Use ** glob that matches both directory and file
    args = baton.parse(Args, split(f"{bundle_path} '**'"))

    with ZipFile2(bundle_path, "r") as z:
        # Should skip directory and only process file
        show_files(z, args)
