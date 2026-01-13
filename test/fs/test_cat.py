"""Test fs cat command."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch
import json

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.fs.cat import Args
from cosmofy.fs.cat import file_to_dict
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


def test_file_to_dict_text() -> None:
    """Test file_to_dict with text content."""
    result = file_to_dict("test.txt", b"hello world")
    assert result["filename"] == "test.txt"
    assert result["size"] == 11
    assert result["contents"] == "hello world"
    assert result["encoding"] == "utf-8"


def test_file_to_dict_binary() -> None:
    """Test file_to_dict with binary content uses base64."""
    binary_data = bytes([0xFF, 0xFE, 0x00, 0x01])
    result = file_to_dict("data.bin", binary_data)
    assert result["filename"] == "data.bin"
    assert result["size"] == 4
    assert result["encoding"] == "base64"
    # Contents should be base64-encoded
    import base64

    assert base64.b64decode(result["contents"]) == binary_data


def test_show_files_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test show_files with JSON output format."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "hello")

    args = baton.parse(Args, split(f"{bundle_path} test.txt --output-format json"))

    with ZipFile2(bundle_path, "r") as z:
        show_files(z, args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["filename"] == "test.txt"
    assert data[0]["contents"] == "hello"
    assert data[0]["encoding"] == "utf-8"


def test_show_files_json_multiple_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test show_files JSON output with multiple files."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("a.txt", "alpha")
        z.writestr("b.txt", "beta")

    args = baton.parse(Args, split(f"{bundle_path} a.txt b.txt --output-format json"))

    with ZipFile2(bundle_path, "r") as z:
        show_files(z, args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 2
    filenames = [d["filename"] for d in data]
    assert "a.txt" in filenames
    assert "b.txt" in filenames
