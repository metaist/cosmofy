"""Test updater remove command."""

# std
from pathlib import Path
from shlex import split

# lib

# pkg
from cosmofy import baton
from cosmofy.updater.add import PATH_COSMOFY
from cosmofy.updater.remove import Args
from cosmofy.updater.remove import remove_arg_prefix
from cosmofy.updater.remove import run
from cosmofy.zipfile2 import ZipFile2


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip"))
    assert args.bundle == Path("bundle.zip")
    assert args.no_args is False


def test_arg_parsing_no_args() -> None:
    """Test Args parsing with --no-args."""
    args = baton.parse(Args, split("bundle.zip --no-args"))
    assert args.no_args is True


def test_remove_arg_prefix_v020() -> None:
    """Test remove_arg_prefix removes v0.2.0 prefix."""
    result = remove_arg_prefix("-m cosmofy.updater.run script.py --flag")
    assert result == "script.py --flag"


def test_remove_arg_prefix_v010() -> None:
    """Test remove_arg_prefix removes v0.1.0 prefix."""
    result = remove_arg_prefix("-m cosmofy.updater -m mymodule")
    assert result == "-m mymodule"


def test_remove_arg_prefix_no_match() -> None:
    """Test remove_arg_prefix returns unchanged if no prefix."""
    result = remove_arg_prefix("-m mymodule")
    assert result == "-m mymodule"


def test_remove_arg_prefix_empty() -> None:
    """Test remove_arg_prefix with empty string."""
    result = remove_arg_prefix("")
    assert result == ""


def test_run_success(tmp_path: Path) -> None:
    """Test run command removes cosmofy package."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "keep")
        z.writestr(f"{PATH_COSMOFY}/__init__.py", "cosmofy")
        z.writestr(f"{PATH_COSMOFY}/updater/__init__.py", "updater")
        # .args format: each argument on its own line
        z.writestr(".args", "-m\ncosmofy.updater.run\n-m\nmymodule")

    args = baton.parse(Args, split(f"{bundle_path}"))
    result = run(args)
    assert result == 0

    with ZipFile2(bundle_path, "r") as z:
        names = z.namelist()
        # cosmofy package should be removed
        assert not any(PATH_COSMOFY in n for n in names)
        # other files should remain
        assert "test.txt" in names
        # .args should be updated - cosmofy prefix removed
        args_content = z.read(".args").decode("utf-8")
        assert "cosmofy" not in args_content
        assert "mymodule" in args_content


def test_run_with_no_args(tmp_path: Path) -> None:
    """Test run command with --no-args keeps original .args."""
    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "keep")
        z.writestr(f"{PATH_COSMOFY}/__init__.py", "cosmofy")
        # .args format: each argument on its own line
        z.writestr(".args", "-m\ncosmofy.updater.run\n-m\nmymodule")

    args = baton.parse(Args, split(f"{bundle_path} --no-args"))
    result = run(args)
    assert result == 0

    with ZipFile2(bundle_path, "r") as z:
        # cosmofy package should still be removed
        names = z.namelist()
        assert not any(PATH_COSMOFY in n for n in names)
        # .args should not be modified (prefix still there)
        args_content = z.read(".args").decode("utf-8")
        assert "cosmofy" in args_content


def test_run_no_bundle() -> None:
    """Test run command with nonexistent bundle returns error."""
    args = baton.parse(Args, split("nonexistent.zip"))
    result = run(args)
    assert result == 2


def test_run_json_output(tmp_path: Path) -> None:
    """Test run command with JSON output format."""
    import io
    import json
    import sys

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "keep")
        z.writestr(f"{PATH_COSMOFY}/__init__.py", "cosmofy")
        z.writestr(".args", "-m\ncosmofy.updater.run\n-m\nmymodule")

    args = baton.parse(Args, split(f"{bundle_path} --output-format json"))

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
    assert "bundle" in data
    assert "removed" in data
    assert "updated_args" in data
