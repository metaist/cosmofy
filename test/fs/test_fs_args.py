"""Test fs args command."""

# std
from pathlib import Path
from shlex import split
import tempfile

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.fs.args import Args
from cosmofy.fs.args import get_args
from cosmofy.fs.args import run
from cosmofy.fs.args import set_args
from cosmofy.zipfile2 import ZipFile2


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip"))
    assert args.bundle == Path("bundle.zip")
    assert args.val == ""


def test_arg_parsing_with_val() -> None:
    """Test Args parsing with value."""
    args = baton.parse(Args, split("bundle.zip 'script.py --flag'"))
    assert args.val == "script.py --flag"


def test_get_args_empty() -> None:
    """Test get_args when no .args file exists."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("test.txt", "content")

        with ZipFile2(path, "r") as z:
            assert get_args(z) == ""
    finally:
        path.unlink(missing_ok=True)


def test_get_args_single_arg() -> None:
    """Test get_args with single argument."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr(".args", "script.py")

        with ZipFile2(path, "r") as z:
            assert get_args(z) == "script.py"
    finally:
        path.unlink(missing_ok=True)


def test_get_args_multi_line() -> None:
    """Test get_args with multi-line .args file."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr(".args", "-m\nmymodule\n--flag")

        with ZipFile2(path, "r") as z:
            result = get_args(z)
            assert "-m" in result
            assert "mymodule" in result
            assert "--flag" in result
    finally:
        path.unlink(missing_ok=True)


def test_set_args_new() -> None:
    """Test set_args when no .args exists."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            pass

        with ZipFile2(path, "a") as z:
            set_args(z, "-m mymodule")

        with ZipFile2(path, "r") as z:
            content = z.read(".args").decode("utf-8")
            assert "-m" in content
            assert "mymodule" in content
    finally:
        path.unlink(missing_ok=True)


def test_set_args_replace() -> None:
    """Test set_args replaces existing .args."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr(".args", "old_script.py")

        with ZipFile2(path, "a") as z:
            set_args(z, "new_script.py")

        with ZipFile2(path, "r") as z:
            content = z.read(".args").decode("utf-8")
            assert "new_script.py" in content
            assert "old_script.py" not in content
    finally:
        path.unlink(missing_ok=True)


def test_set_args_dry_run() -> None:
    """Test set_args with dry_run doesn't modify."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr(".args", "original")

        with ZipFile2(path, "a") as z:
            set_args(z, "new_value", dry_run=True)

        with ZipFile2(path, "r") as z:
            content = z.read(".args").decode("utf-8")
            assert "original" in content
    finally:
        path.unlink(missing_ok=True)


def test_run_get_args(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test run command in get mode."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr(".args", "script.py")

    args = baton.parse(Args, split(f"{bundle_path}"))
    result = run(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "script.py" in captured.out


def test_run_set_args(tmp_path: Path) -> None:
    """Test run command in set mode."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        pass

    args = baton.parse(Args, split(f"{bundle_path} '-m mymodule'"))
    result = run(args)
    assert result == 0

    with ZipFile2(bundle_path, "r") as z:
        content = z.read(".args").decode("utf-8")
        assert "-m" in content
        assert "mymodule" in content


def test_run_error_no_bundle() -> None:
    """Test run command with nonexistent bundle returns error."""
    args = baton.parse(Args, split("nonexistent.zip"))
    result = run(args)
    assert result == 2
