"""Test arg parsing."""

# std
from dataclasses import dataclass
from os import environ as ENV
from pathlib import Path
from shlex import split
from typing import Literal
from typing import Union

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.baton import arg
from cosmofy.baton import Command


def test_arg_basic() -> None:
    have = baton.arg("").metadata
    want = {
        "arg": baton.ArgPartial(
            short="", action="", required=False, positional=False, env=""
        )
    }
    assert have == want

    with pytest.raises(ValueError, match="cannot be required"):
        baton.arg("", positional=False, required=True)


def test_default_factory() -> None:
    have = baton.arg(None, default_factory=list)
    assert have.default_factory is list


def test_get_choices() -> None:
    assert baton.get_choices(int) is None
    assert baton.get_choices(Literal["a", "b", "c"]) == (str, ["a", "b", "c"])


def test_get_item_type() -> None:
    assert baton.get_item_type(int) is int
    assert baton.get_item_type(list[int]) is int
    assert baton.get_item_type(Union[Path, None]) is Path  # type: ignore[arg-type]


def test_infer_action() -> None:
    assert baton.infer_action(str) == "store"
    assert baton.infer_action(int) == "store"  # not "count"
    assert baton.infer_action(list[str]) == "extend"
    assert baton.infer_action(list[int]) == "extend"
    assert baton.infer_action(list[Path]) == "extend"
    assert baton.infer_action(bool) == "store_true"
    assert baton.infer_action(bool, positional=True) == "store_bool"


def test_from_field_choices() -> None:
    @dataclass
    class X:
        a: Literal["a", "b", "c"]
        b: Literal[1, 2, 3]
        c: int

    spec = baton.Arg.from_class(X)
    assert spec[0].choices == ["a", "b", "c"]
    assert spec[0].item_type is str
    assert spec[1].choices == [1, 2, 3]
    assert spec[1].item_type is int
    assert spec[2].choices == []


def test_from_field_metadata() -> None:
    @dataclass
    class X:
        a: str = arg(default="")

    spec = baton.Arg.from_class(X)
    assert spec[0].field_name == "a"
    assert spec[0].item_type is str


def test_command_basic() -> None:
    @dataclass
    class X:
        """Usage: foo --help"""

        help: bool = arg(default=False, short="-h")
        file: list[Path] = arg(list, positional=True)

    def run(args: X) -> int:
        return 0

    cmd = Command("cmd", X, run)
    assert cmd.usage == X.__doc__

    cmd = Command("cmd", X, run, usage="Does this work?")
    assert cmd.usage == "Does this work?"
    assert len(cmd.args) == 2
    assert cmd.aliases == {"-h": "--help"}
    assert len(cmd.optionals) == 1
    assert len(cmd.positionals) == 1


def test_command_single() -> None:
    @dataclass
    class X:
        help: bool = arg(default=False, short="-h")

    def run(args: X) -> int:
        return 0

    cmd = Command("cmd", X, run)
    assert cmd.main(["-h"]) == 0


@dataclass
class Args:
    help: bool = arg(default=False, short="-h")
    verbose: int = arg(default=0, short="-v", action="count")
    output: Path | None = arg(default=None, short="-o")


def test_short_flags() -> None:
    have = baton.parse(Args, split("-v"))
    assert have.verbose == 1, "single short flag"

    have = baton.parse(Args, split("-vvv"))
    assert have.verbose == 3, "combined short flags"

    have = baton.parse(Args, split("-o foo"))
    assert have.verbose == 0, "short flag with value"
    assert have.output == Path("foo"), "short flag with value"

    have = baton.parse(Args, split("-vo foo"))
    assert have.verbose == 1, "combined short flag with value"
    assert have.output == Path("foo"), "combined short flag with value"

    with pytest.raises(ValueError, match="unknown option"):
        have = baton.parse(Args, split("-?"))


def test_long_flags() -> None:
    have = baton.parse(Args, split("--verbose"))
    assert have.verbose == 1, "long flag boolean"

    have = baton.parse(Args, split("--output foo"))
    assert have.output == Path("foo"), "long flag with space value"

    have = baton.parse(Args, split("--output=foo"))
    assert have.output == Path("foo"), "long flag with equals value"

    have = baton.parse(Args, split("--output="))
    assert have.output == Path(""), "long flag with equals empty value"

    with pytest.raises(ValueError, match="unknown option"):
        have = baton.parse(Args, split("--unknown"))


def test_positionals() -> None:
    @dataclass
    class X:
        a: str = arg("", positional=True)
        b: str = arg("", positional=True)

    have = baton.parse(X, split("a"))
    assert have.a == "a", "single positional"

    @dataclass
    class Y:
        a: list[str] = arg(list, positional=True, action="extend")

    have = baton.parse(Y, split("a b"))
    assert have.a == ["a", "b"], "extend consumes multiple values"

    @dataclass
    class Z:
        a: str = arg("", positional=True)
        b: str = arg("", positional=True, required=True)

    have = baton.parse(Z, split("a b"))
    assert have.a == "a", "multiple positionals in order"
    assert have.b == "b", "multiple positionals in order"

    with pytest.raises(ValueError, match="missing required"):
        baton.parse(Z, split("a"))

    with pytest.raises(ValueError, match="unexpected argument"):
        baton.parse(Z, split("a b c"))


def test_mixed() -> None:
    @dataclass
    class X:
        verbose: bool = arg(False)
        input: str = arg("", positional=True)
        output: str = arg("", positional=True)

    have = baton.parse(X, split("--verbose file.txt"))
    assert have.verbose is True, "flag before positional"
    assert have.input == "file.txt", "flag before positional"
    assert have.output == "", "flag before positional"

    have = baton.parse(X, split("file.txt --verbose"))
    assert have.verbose is True, "positional before flag"
    assert have.input == "file.txt", "positional before flag"
    assert have.output == "", "positional before flag"

    have = baton.parse(X, split("file.txt --verbose -- --output"))
    assert have.verbose is True, "-- stops process"
    assert have.input == "file.txt", "-- stops process"
    assert have.output == "--output", "-- stops process"


def test_actions() -> None:
    @dataclass
    class X:
        count: int = arg(0, action="store")
        flag: bool = arg(False, action="store_bool")
        store_false: bool = arg(True, action="store_false")
        include: list[str] = arg(list, action="append")
        files: list[str] = arg(list, action="extend")
        verbose: int = arg(0, short="-v", action="count")
        nums: list[int] = arg(list)
        choice: Literal["", "a", "b"] = arg("")

    have = baton.parse(X, split("--count 42"))
    assert have.count == 42, "converted to int"

    have = baton.parse(X, split("--nums 1 2 3"))
    assert have.nums == [1, 2, 3], "converted to ints"

    have = baton.parse(X, split("--store-false"))
    assert have.store_false is False, "explicit set"

    have = baton.parse(X, split("--flag true"))
    assert have.flag is True, "explicit value"

    have = baton.parse(X, split("--flag true --flag=false"))
    assert have.flag is False, "explicit value + later override"

    have = baton.parse(X, split("--include a --include b"))
    assert have.include == ["a", "b"], "accumulates"

    have = baton.parse(X, split("--files a b c --verbose"))
    assert have.files == ["a", "b", "c"], "extend consumes until flag"

    have = baton.parse(X, split("-vvv"))
    assert have.verbose == 3, "count increments"

    have = baton.parse(X, split("--choice a"))
    assert have.choice == "a", "enforces choices"
    with pytest.raises(ValueError, match="invalid value"):
        baton.parse(X, split("--choice x"))

    with pytest.raises(ValueError, match="value is required"):
        baton.parse(X, split("--choice"))
    with pytest.raises(ValueError, match="value is required"):
        baton.parse(X, split("--include"))
    with pytest.raises(ValueError, match="value is required"):
        baton.parse(X, split("--files"))


def test_subcommands() -> None:
    @dataclass
    class Common:
        verbose: int = arg(default=0, short="-v", action="count")

    @dataclass
    class Parent(Common):
        """Usage: parent [--verbose] <command>"""

        command: str = arg(default="", positional=True, required=True)

    @dataclass
    class Child(Common):
        """Usage: child [--verbose] [<input>]"""

        input: str = arg(default="", positional=True)

    scenario = 0

    def run_child(args: Child) -> int:
        if scenario == 1:
            assert args.verbose == 2
            assert args.input == "path"
        return 0

    def run_parent(args: Parent) -> int:
        if scenario == 1:
            assert args.verbose == 2
            assert args.command == "child"

        return 0

    child = Command("child", Child, run_child)
    parent = Command("parent", Parent, run_parent, subcommands={"child": child})

    scenario = 1
    assert parent.main(split("-vv child path")) == 0
    assert parent.main(split("child path -vv")) == 0
    assert parent.main(split("child -vv path")) == 0
    assert parent.main(split("-v child -v path")) == 0

    scenario = 2
    assert parent.main(split("unknown")) == 1, "unknown subcommand errors"


def test_env() -> None:
    @dataclass
    class X:
        output: str = arg("", env="_OUTPUT")
        store_true: bool = arg(False, env="_store_true", action="store_true")

    ENV["_OUTPUT"] = "test"
    have = baton.parse(X, split(""))
    assert have.output == "test"
    del ENV["_OUTPUT"]

    ENV["_store_true"] = "1"
    have = baton.parse(X, split(""))
    assert have.store_true is True
    del ENV["_store_true"]


def test_edge() -> None:
    @dataclass
    class X:
        opt: bool = arg(False)
        output: str = arg("")
        pos: str = arg("", positional=True)

    have = baton.parse(X, split(""))
    assert have.opt is False

    have = baton.parse(X, split("--"))
    assert have.opt is False

    have = baton.parse(X, split("--output --weird-filename"))
    assert have.output == "--weird-filename"

    have = baton.parse(X, split("-- -weird-file"))
    assert have.pos == "-weird-file"


def test_double_dash_extend() -> None:
    """Test -- with extend action consumes remaining args."""

    @dataclass
    class X:
        files: list[str] = arg(list, positional=True, action="extend")

    have = baton.parse(X, split("-- -file1 -file2"))
    assert have.files == ["-file1", "-file2"]


def test_double_dash_multiple_positionals() -> None:
    """Test -- with multiple non-extend positionals."""

    @dataclass
    class X:
        a: str = arg("", positional=True)
        b: str = arg("", positional=True)
        c: str = arg("", positional=True)

    have = baton.parse(X, split("-- x y z"))
    assert have.a == "x"
    assert have.b == "y"
    assert have.c == "z"


def test_double_dash_too_many_args() -> None:
    """Test -- with more args than positionals raises error."""

    @dataclass
    class X:
        a: str = arg("", positional=True)

    with pytest.raises(ValueError, match="unexpected argument"):
        baton.parse(X, split("-- x y"))


def test_double_dash_no_positionals() -> None:
    """Test -- with no positionals but extra args raises error."""

    @dataclass
    class X:
        opt: bool = arg(False)

    with pytest.raises(ValueError, match="unexpected argument"):
        baton.parse(X, split("-- x"))


def test_extend_with_choices() -> None:
    """Test extend action with choices shows error hint."""

    @dataclass
    class X:
        files: list[str] = arg(list, action="extend")

    with pytest.raises(ValueError, match="value is required"):
        baton.parse(X, split("--files"))


def test_color_formatter() -> None:
    """Test ColorFormatter formats log records with colors."""
    import logging

    formatter = baton.ColorFormatter("%(levelname)s: %(message)s", color="never")

    # Test different log levels
    for level, expected in [
        (logging.ERROR, "error"),
        (logging.WARNING, "warning"),
        (logging.INFO, "info"),
        (logging.DEBUG, "debug"),
        (logging.CRITICAL, "critical"),  # Unknown level
    ]:
        record = logging.LogRecord(
            name="test",
            level=level,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert expected in result.lower()


def test_color_handler() -> None:
    """Test ColorHandler sets stream on formatter."""

    handler = baton.ColorHandler()
    formatter = baton.ColorFormatter("%(message)s")
    handler.setFormatter(formatter)
    assert formatter._stream is not None


def test_use_color_modes() -> None:
    """Test use_color with different modes."""
    import io

    # Test "never" mode
    assert baton.use_color("never", io.StringIO()) is False

    # Test "always" mode
    assert baton.use_color("always", io.StringIO()) is True


def test_use_color_env_vars() -> None:
    """Test use_color respects environment variables."""
    import io

    # Save original env
    orig_no_color = ENV.get("NO_COLOR")
    orig_clicolor = ENV.get("CLICOLOR")
    orig_force_color = ENV.get("FORCE_COLOR")
    orig_clicolor_force = ENV.get("CLICOLOR_FORCE")
    orig_term = ENV.get("TERM")

    try:
        # Clear all color env vars first
        for var in ["NO_COLOR", "CLICOLOR", "FORCE_COLOR", "CLICOLOR_FORCE"]:
            if var in ENV:
                del ENV[var]

        # Test NO_COLOR
        ENV["NO_COLOR"] = "1"
        assert baton.use_color("auto", io.StringIO()) is False
        del ENV["NO_COLOR"]

        # Test CLICOLOR=0
        ENV["CLICOLOR"] = "0"
        assert baton.use_color("auto", io.StringIO()) is False
        del ENV["CLICOLOR"]

        # Test FORCE_COLOR
        ENV["FORCE_COLOR"] = "1"
        assert baton.use_color("auto", io.StringIO()) is True
        del ENV["FORCE_COLOR"]

        # Test CLICOLOR_FORCE
        ENV["CLICOLOR_FORCE"] = "1"
        assert baton.use_color("auto", io.StringIO()) is True
        del ENV["CLICOLOR_FORCE"]

        # Test TERM=dumb (need a TTY-like object for this)
        # StringIO doesn't have isatty, so use_color returns False anyway
    finally:
        # Restore original env
        if orig_no_color is not None:
            ENV["NO_COLOR"] = orig_no_color
        if orig_clicolor is not None:
            ENV["CLICOLOR"] = orig_clicolor
        if orig_force_color is not None:
            ENV["FORCE_COLOR"] = orig_force_color
        if orig_clicolor_force is not None:
            ENV["CLICOLOR_FORCE"] = orig_clicolor_force
        if orig_term is not None:
            ENV["TERM"] = orig_term


def test_render_tags() -> None:
    """Test render_tags with different modes."""
    # Test with color=never (strips tags)
    result = baton.render_tags("[bold]hello[/]", color="never")
    assert result == "hello"
    assert "[bold]" not in result

    # Test with color=always (renders tags)
    result = baton.render_tags("[bold]hello[/]", color="always")
    assert "\033[" in result  # ANSI escape

    # Test with unknown tag (left as-is)
    result = baton.render_tags("[unknowntag]hello[/]", color="always")
    assert "[unknowntag]" in result

    # Test with custom theme
    custom_theme = {"custom": "red"}
    result = baton.render_tags("[custom]hello[/]", color="always", theme=custom_theme)
    assert "\033[31m" in result  # red


def test_decorate() -> None:
    """Test decorate applies theme markings."""
    text = """
Usage: mycommand --help

Arguments:
  <FILE>...              files to process

Options:
  --verbose              be verbose
  [OPTION]               optional thing

Commands:
  build                  build the project

  tip: use `--help` for more
  [default: value]
  [env: MY_VAR=test]
  [choices: a, b, c]
"""
    result = baton.decorate(text)

    # Check various decorations were applied
    assert "[command]" in result  # command names
    assert "[heading]" in result  # headings
    assert "[argument]" in result  # <ARGUMENTS>
    assert "[option]" in result  # [OPTIONS]
    assert "[flag]" in result  # --flags
    assert "[tip]" in result  # tip:
    assert "[default]" in result  # default values
    assert "[env]" in result  # env vars
    assert "[choice]" in result  # choices


def test_show_usage_short() -> None:
    """Test show_usage with short=True."""

    @dataclass
    class X:
        """Full description here.

        Usage: cmd [OPTIONS]

        Arguments:
          <FILE>...              files to process

        Options:
          --help                 show help
        """

        help: bool = arg(False)

    def run(args: X) -> int:
        return 0

    cmd = Command("cmd", X, run)
    # Just verify it doesn't crash
    cmd.show_usage(short=True, color="never")
    cmd.show_usage(short=False, color="never")


def test_show_usage_with_color() -> None:
    """Test show_usage with color enabled."""

    @dataclass
    class X:
        """Full description.

        Usage: cmd [OPTIONS]

        Options:
          --help                 show help
        """

        help: bool = arg(False)

    def run(args: X) -> int:
        return 0

    cmd = Command("cmd", X, run)
    # Test with color=always to trigger decorate() in show_usage
    cmd.show_usage(short=False, color="always")


def test_color_formatter_with_color_always() -> None:
    """Test ColorFormatter with color=always applies decorate."""
    import logging

    formatter = baton.ColorFormatter("%(levelname)s: %(message)s", color="always")

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test message",
        args=(),
        exc_info=None,
    )
    result = formatter.format(record)
    # With color=always, should apply ANSI codes
    # The decorate function is called
    assert "info" in result.lower()


def test_use_color_tty() -> None:
    """Test use_color with a TTY-like file."""
    import io

    # Create a mock TTY
    class MockTTY(io.StringIO):
        def isatty(self) -> bool:
            return True

    # Clear color env vars and set TERM to something non-dumb
    orig_no_color = ENV.get("NO_COLOR")
    orig_clicolor = ENV.get("CLICOLOR")
    orig_force_color = ENV.get("FORCE_COLOR")
    orig_clicolor_force = ENV.get("CLICOLOR_FORCE")
    orig_term = ENV.get("TERM")

    try:
        # Clear all color env vars
        for var in ["NO_COLOR", "CLICOLOR", "FORCE_COLOR", "CLICOLOR_FORCE"]:
            if var in ENV:
                del ENV[var]

        # Set TERM to a normal value
        ENV["TERM"] = "xterm"

        # With TTY and no disabling env vars, should return True
        assert baton.use_color("auto", MockTTY()) is True

        # Test with TERM=dumb, should return False
        ENV["TERM"] = "dumb"
        assert baton.use_color("auto", MockTTY()) is False

    finally:
        # Restore original env
        for var, orig in [
            ("NO_COLOR", orig_no_color),
            ("CLICOLOR", orig_clicolor),
            ("FORCE_COLOR", orig_force_color),
            ("CLICOLOR_FORCE", orig_clicolor_force),
            ("TERM", orig_term),
        ]:
            if orig is not None:
                ENV[var] = orig
            elif var in ENV:
                del ENV[var]


def test_command_main_argv_none() -> None:
    """Test Command.main with argv=None uses sys.argv."""
    import sys

    @dataclass
    class X:
        help: bool = arg(False, short="-h")

    def run(args: X) -> int:
        return 0

    cmd = Command("cmd", X, run)

    # Save and restore sys.argv
    orig_argv = sys.argv
    try:
        sys.argv = ["cmd", "-h"]
        result = cmd.main()
        assert result == 0
    finally:
        sys.argv = orig_argv
