"""Test bundle."""

# std
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch

# pkg
from cosmofy import baton
from cosmofy.bundle import Args
from cosmofy.bundle import Bundler
from cosmofy.fs.add import Args as FsAddArgs


def test_suffix_arg_parsing() -> None:
    """Test --suffix argument parsing."""
    have = baton.parse(Args, split(""))
    assert have.suffix is None, "default is None"

    have = baton.parse(Args, split("--suffix .exe"))
    assert have.suffix == ".exe", "explicit suffix"

    have = baton.parse(Args, split("-s .com"))
    assert have.suffix == ".com", "short flag"

    have = baton.parse(Args, split("--suffix="))
    assert have.suffix == "", "explicit empty suffix"


@patch("cosmofy.bundle.platform.system")
def test_suffix_default_windows(mock_system: MagicMock) -> None:
    """Test default suffix on Windows."""
    mock_system.return_value = "Windows"
    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    assert bundler.suffix == ".com", "default .com on Windows"


@patch("cosmofy.bundle.platform.system")
def test_suffix_default_linux(mock_system: MagicMock) -> None:
    """Test default suffix on Linux."""
    mock_system.return_value = "Linux"
    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    assert bundler.suffix == "", "default empty on Linux"


@patch("cosmofy.bundle.platform.system")
def test_suffix_default_darwin(mock_system: MagicMock) -> None:
    """Test default suffix on macOS."""
    mock_system.return_value = "Darwin"
    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    assert bundler.suffix == "", "default empty on macOS"


@patch("cosmofy.bundle.platform.system")
def test_suffix_explicit_override(mock_system: MagicMock) -> None:
    """Test explicit suffix overrides platform default."""
    mock_system.return_value = "Windows"
    args = baton.parse(Args, split("--suffix .exe"))
    bundler = Bundler(args)
    assert bundler.suffix == ".exe", "explicit suffix overrides default"


@patch("cosmofy.bundle.platform.system")
def test_suffix_explicit_empty_on_windows(mock_system: MagicMock) -> None:
    """Test explicit empty suffix on Windows."""
    mock_system.return_value = "Windows"
    args = baton.parse(Args, split("--suffix="))
    bundler = Bundler(args)
    assert bundler.suffix == "", "explicit empty suffix on Windows"


def test_compile_bytecode_arg_parsing() -> None:
    """Test --compile-bytecode argument parsing for bundle."""
    have = baton.parse(Args, split(""))
    assert have.compile_bytecode is False, "default is False"

    have = baton.parse(Args, split("--compile-bytecode"))
    assert have.compile_bytecode is True, "long flag"

    have = baton.parse(Args, split("-c"))
    assert have.compile_bytecode is True, "short flag"


def test_fs_add_compile_bytecode_arg_parsing() -> None:
    """Test --compile-bytecode argument parsing for fs add."""
    have = baton.parse(FsAddArgs, split("bundle.zip file.py"))
    assert have.compile_bytecode is False, "default is False"

    have = baton.parse(FsAddArgs, split("bundle.zip --compile-bytecode file.py"))
    assert have.compile_bytecode is True, "long flag"

    have = baton.parse(FsAddArgs, split("bundle.zip -c file.py"))
    assert have.compile_bytecode is True, "short flag"
