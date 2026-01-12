"""Test self version command."""

# std
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.self.version import Args
from cosmofy.self.version import get_version
from cosmofy.self.version import print_version
from cosmofy.self.version import run


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split(""))
    assert args.short is False
    assert args.output_format == "text"


def test_arg_parsing_short() -> None:
    """Test Args parsing with --short."""
    args = baton.parse(Args, split("--short"))
    assert args.short is True


def test_arg_parsing_json() -> None:
    """Test Args parsing with --output-format json."""
    args = baton.parse(Args, split("--output-format json"))
    assert args.output_format == "json"


def test_get_version() -> None:
    """Test get_version returns package metadata."""
    data = get_version()
    assert "package_name" in data
    assert "version" in data
    assert data["package_name"] == "cosmofy"


def test_print_version_text(capsys: pytest.CaptureFixture[str]) -> None:
    """Test print_version with text format."""
    result = print_version(output_format="text", color="never")
    captured = capsys.readouterr()
    assert "cosmofy" in result
    assert "cosmofy" in captured.out


def test_print_version_short(capsys: pytest.CaptureFixture[str]) -> None:
    """Test print_version with short flag."""
    result = print_version(short=True, output_format="text", color="never")
    captured = capsys.readouterr()
    # Short version doesn't include package name
    assert "cosmofy " not in result
    assert result in captured.out


def test_print_version_json() -> None:
    """Test print_version with json format."""
    result = print_version(output_format="json")
    assert "package_name" in result
    assert "version" in result
    assert "{" in result  # JSON format


def test_run_success() -> None:
    """Test run command success."""
    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 0


def test_run_json() -> None:
    """Test run command with json output."""
    args = baton.parse(Args, split("--output-format json"))
    result = run(args)
    assert result == 0


def test_run_short() -> None:
    """Test run command with short flag."""
    args = baton.parse(Args, split("--short"))
    result = run(args)
    assert result == 0


@patch("cosmofy.self.version.print_version")
def test_run_error(mock_print: MagicMock) -> None:
    """Test run command handles errors."""
    mock_print.side_effect = RuntimeError("Test error")
    args = baton.parse(Args, split(""))
    result = run(args)
    assert result == 2
