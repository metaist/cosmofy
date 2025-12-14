"""Test arg parsing."""

# std
from dataclasses import dataclass
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
    want = {"arg": baton.ArgMetadata()}
    assert have == want

    with pytest.raises(ValueError, match="cannot be required"):
        baton.arg("", positional=False, required=True)


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

    with pytest.raises(ValueError, match="Unknown option"):
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

    with pytest.raises(ValueError, match="Unknown option"):
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

    with pytest.raises(ValueError, match="Missing required"):
        baton.parse(Z, split("a"))

    with pytest.raises(ValueError, match="Unexpected argument"):
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
        include: list[str] = arg(list, action="append")
        files: list[str] = arg(list, action="extend")
        verbose: int = arg(0, short="-v", action="count")
        nums: list[int] = arg(list)
        choice: Literal["", "a", "b"] = arg("")

    have = baton.parse(X, split("--count 42"))
    assert have.count == 42, "converted to int"

    have = baton.parse(X, split("--nums 1 2 3"))
    assert have.nums == [1, 2, 3], "converted to ints"

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
    with pytest.raises(ValueError, match="Invalid value"):
        baton.parse(X, split("--choice x"))
