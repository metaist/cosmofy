"""Test shell completion generation."""

# std
from dataclasses import dataclass

# lib
import pytest

# pkg
from cosmofy import completions
from cosmofy.baton import arg
from cosmofy.baton import Command


SAMPLE_USAGE = """\
Sample command for testing.

Usage: sample [OPTIONS] <FILE> [OUTPUT]

Arguments:
  <FILE>                    input file to process
  [OUTPUT]                  output file (optional)

Options:
  -v, --verbose             enable verbose output
  -o, --output <PATH>       output path
      --format <MODE>       output format
                            [choices: json, text, csv]
      --level <NUM>         compression level
                            [default: 5]

Global options:
  -h, --help                show this help message
"""


def test_parse_flags_basic() -> None:
    """Test parsing basic flags from usage."""
    flags = completions.parse_flags(SAMPLE_USAGE)

    # Should find -v/--verbose, -o/--output, --format, --level, -h/--help
    assert len(flags) >= 4

    # Check verbose flag
    verbose = next((f for f in flags if f.long == "--verbose"), None)
    assert verbose is not None
    assert verbose.short == "-v"
    assert verbose.takes_value is False
    assert verbose.description == "enable verbose output"

    # Check output option with value
    output = next((f for f in flags if f.long == "--output"), None)
    assert output is not None
    assert output.short == "-o"
    assert output.takes_value is True
    assert output.placeholder == "PATH"

    # Check format option (choices on same line work)
    fmt = next((f for f in flags if f.long == "--format"), None)
    assert fmt is not None
    assert fmt.takes_value is True
    # Note: choices on continuation lines aren't captured by current parser


def test_parse_flags_empty() -> None:
    """Test parsing flags from usage with no options."""
    usage = "Usage: cmd <FILE>"
    flags = completions.parse_flags(usage)
    assert flags == []


def test_parse_positionals_basic() -> None:
    """Test parsing positional arguments."""
    positionals = completions.parse_positionals(SAMPLE_USAGE)

    assert len(positionals) == 2

    # FILE is required
    assert positionals[0].name == "FILE"
    assert positionals[0].required is True
    assert positionals[0].repeatable is False

    # OUTPUT is optional
    assert positionals[1].name == "OUTPUT"
    assert positionals[1].required is False


def test_parse_positionals_repeatable() -> None:
    """Test parsing repeatable positional arguments."""
    # Note: Current regex doesn't capture ... after closing bracket
    # This tests the current behavior; repeatable detection is a future enhancement
    usage = "Usage: cmd [FILE]..."
    positionals = completions.parse_positionals(usage)

    assert len(positionals) == 1
    assert positionals[0].name == "FILE"
    # repeatable is not captured by current regex pattern
    assert positionals[0].repeatable is False


def test_parse_positionals_with_choices() -> None:
    """Test parsing positional with choices."""
    usage = """\
Usage: cmd <MODE>

Arguments:
  <MODE>                    mode to use [choices: fast, slow]
"""
    positionals = completions.parse_positionals(usage)
    assert len(positionals) == 1
    assert positionals[0].choices == ["fast", "slow"]


def test_parse_positionals_skips_options() -> None:
    """Test that [OPTIONS] is not parsed as a positional."""
    usage = "Usage: cmd [OPTIONS] <FILE>"
    positionals = completions.parse_positionals(usage)

    assert len(positionals) == 1
    assert positionals[0].name == "FILE"


def test_get_subcommands() -> None:
    """Test extracting subcommand info."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        """Child command description."""

        pass

    def noop(_: object) -> int:
        return 0

    child = Command("child", Child, noop)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    subcommands = completions.get_subcommands(parent)
    assert "child" in subcommands
    assert subcommands["child"] == "Child command description."


def test_get_subcommands_empty() -> None:
    """Test with no subcommands."""

    @dataclass
    class Cmd:
        pass

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop)
    subcommands = completions.get_subcommands(cmd)
    assert subcommands == {}


def test_get_completion_type() -> None:
    """Test mapping placeholders to completion types."""
    # File-related placeholders
    assert completions.get_completion_type("FILE", []) == "file"
    assert completions.get_completion_type("PATH", []) == "file"
    assert completions.get_completion_type("BUNDLE", []) == "file"
    assert completions.get_completion_type("SCRIPT", []) == "file"

    # Directory placeholders
    assert completions.get_completion_type("DIR", []) == "directory"
    assert completions.get_completion_type("DIRECTORY", []) == "directory"

    # With choices
    assert completions.get_completion_type("MODE", ["a", "b"]) == "choices"

    # Unknown placeholder
    assert completions.get_completion_type("UNKNOWN", []) == "none"


def test_generate_bash() -> None:
    """Test bash completion generation."""

    @dataclass
    class Cmd:
        """Test command."""

        verbose: bool = arg(False, short="-v")
        output: str = arg("", short="-o")

    def noop(_: object) -> int:
        return 0

    cmd = Command("testcmd", Cmd, noop, SAMPLE_USAGE)
    result = completions.generate_bash(cmd)

    assert "# Bash completion for testcmd" in result
    assert "_testcmd_completions()" in result
    assert "complete -F _testcmd_completions testcmd" in result
    assert "COMPREPLY=" in result
    assert "compgen" in result


def test_generate_bash_with_subcommands() -> None:
    """Test bash completion with subcommands."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        """Child."""

        pass

    def noop(_: object) -> int:
        return 0

    child = Command("child", Child, noop)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_bash(parent)
    assert "child" in result


def test_generate_zsh() -> None:
    """Test zsh completion generation."""

    @dataclass
    class Cmd:
        """Test command."""

        verbose: bool = arg(False, short="-v")

    def noop(_: object) -> int:
        return 0

    cmd = Command("testcmd", Cmd, noop, SAMPLE_USAGE)
    result = completions.generate_zsh(cmd)

    assert "#compdef testcmd" in result
    assert "_testcmd()" in result
    assert "_arguments" in result


def test_generate_zsh_with_subcommands() -> None:
    """Test zsh completion with subcommands."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        """Child command."""

        pass

    def noop(_: object) -> int:
        return 0

    child = Command("child", Child, noop)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_zsh(parent)
    assert "_describe 'command' subcmds" in result
    assert "_parent_child" in result


def test_generate_fish() -> None:
    """Test fish completion generation."""

    @dataclass
    class Cmd:
        """Test command."""

        verbose: bool = arg(False, short="-v")

    def noop(_: object) -> int:
        return 0

    cmd = Command("testcmd", Cmd, noop, SAMPLE_USAGE)
    result = completions.generate_fish(cmd)

    assert "# Fish completion for testcmd" in result
    assert "complete -c testcmd" in result


def test_generate_fish_with_subcommands() -> None:
    """Test fish completion with subcommands."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        """Child command."""

        pass

    def noop(_: object) -> int:
        return 0

    child = Command("child", Child, noop)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_fish(parent)
    assert "__fish_use_subcommand" in result
    assert "-a 'child'" in result


def test_generate_completions_bash() -> None:
    """Test generate_completions with bash."""

    @dataclass
    class Cmd:
        pass

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop)
    result = completions.generate_completions(cmd, "bash")
    assert "# Bash completion" in result


def test_generate_completions_zsh() -> None:
    """Test generate_completions with zsh."""

    @dataclass
    class Cmd:
        pass

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop)
    result = completions.generate_completions(cmd, "zsh")
    assert "#compdef" in result


def test_generate_completions_fish() -> None:
    """Test generate_completions with fish."""

    @dataclass
    class Cmd:
        pass

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop)
    result = completions.generate_completions(cmd, "fish")
    assert "# Fish completion" in result


def test_command_run(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the completions command run function."""
    args = completions.Args(shell="bash")  # type: ignore[arg-type]
    result = completions.run(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "# Bash completion for cosmofy" in captured.out


def test_command_run_zsh(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the completions command with zsh."""
    args = completions.Args(shell="zsh")  # type: ignore[arg-type]
    result = completions.run(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "#compdef cosmofy" in captured.out


def test_command_run_fish(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the completions command with fish."""
    args = completions.Args(shell="fish")  # type: ignore[arg-type]
    result = completions.run(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "# Fish completion for cosmofy" in captured.out


def test_command_run_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the completions command with JSON output format."""
    args = completions.Args(shell="bash", output_format="json")  # type: ignore[arg-type]
    result = completions.run(args)

    assert result == 0
    captured = capsys.readouterr()
    import json

    data = json.loads(captured.out)
    assert data["shell"] == "bash"
    assert "# Bash completion for cosmofy" in data["script"]


def test_flag_info_dataclass() -> None:
    """Test FlagInfo dataclass."""
    flag = completions.FlagInfo(
        short="-v",
        long="--verbose",
        takes_value=False,
        placeholder="",
        choices=[],
        description="verbose mode",
    )
    assert flag.short == "-v"
    assert flag.long == "--verbose"


def test_positional_info_dataclass() -> None:
    """Test PositionalInfo dataclass."""
    pos = completions.PositionalInfo(
        name="FILE",
        required=True,
        repeatable=False,
        choices=[],
    )
    assert pos.name == "FILE"
    assert pos.required is True


def test_bash_with_choices() -> None:
    """Test bash completion with options that have choices."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
      --format <MODE>       [choices: json, text]
"""

    @dataclass
    class Cmd:
        format: str = arg("")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_bash(cmd)

    # Should have choice completion for --format
    assert "json text" in result


def test_bash_with_file_option() -> None:
    """Test bash completion with file-type options."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
  -o, --output <FILE>       output file
"""

    @dataclass
    class Cmd:
        output: str = arg("", short="-o")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_bash(cmd)

    # Should have file completion for --output
    assert "_filedir" in result


def test_bash_with_directory_option() -> None:
    """Test bash completion with directory-type options."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
      --dir <DIR>           directory path
"""

    @dataclass
    class Cmd:
        dir: str = arg("")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_bash(cmd)

    # Should have directory completion for --dir
    assert "_filedir -d" in result


def test_zsh_with_file_option() -> None:
    """Test zsh completion with file-type options."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
  -o, --output <FILE>       output file
"""

    @dataclass
    class Cmd:
        output: str = arg("", short="-o")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_zsh(cmd)

    # Should have file completion
    assert ":file:_files" in result


def test_fish_with_file_option() -> None:
    """Test fish completion with file-type options."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
  -o, --output <FILE>       output file
"""

    @dataclass
    class Cmd:
        output: str = arg("", short="-o")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_fish(cmd)

    # Should have file completion flag
    assert "-r -F" in result


def test_nested_subcommand_name() -> None:
    """Test command name with dots gets split correctly."""

    @dataclass
    class Cmd:
        pass

    def noop(_: object) -> int:
        return 0

    cmd = Command("cosmofy.fs.ls", Cmd, noop)
    result = completions.generate_bash(cmd)

    # Should use root name 'cosmofy'
    assert "_cosmofy_completions" in result
    assert "complete -F _cosmofy_completions cosmofy" in result


def test_zsh_subcommand_function() -> None:
    """Test zsh generates subcommand functions."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        """Child help."""

        verbose: bool = arg(False, short="-v")

    def noop(_: object) -> int:
        return 0

    child_usage = """\
Child command.

Usage: parent child [OPTIONS]

Options:
  -v, --verbose             verbose
"""
    child = Command("child", Child, noop, child_usage)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_zsh(parent)
    assert "_parent_child()" in result


def test_fish_subcommand_options() -> None:
    """Test fish generates options for subcommands."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        verbose: bool = arg(False, short="-v")

    def noop(_: object) -> int:
        return 0

    child_usage = """\
Child command.

Usage: parent child [OPTIONS]

Options:
  -v, --verbose             verbose mode
"""
    child = Command("child", Child, noop, child_usage)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_fish(parent)
    assert "__fish_seen_subcommand_from child" in result
    assert "-s v" in result or "-l verbose" in result


def test_bash_with_dir_positional() -> None:
    """Test bash completion with directory positional."""
    usage = """\
Usage: cmd <DIR>

Arguments:
  <DIR>                     directory path
"""

    @dataclass
    class Cmd:
        dir: str = arg("", positional=True)

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_bash(cmd)

    # Should have directory completion for positional
    assert "_filedir -d" in result


def test_bash_with_choices_positional() -> None:
    """Test bash completion with choices positional."""
    usage = """\
Usage: cmd <MODE>

Arguments:
  <MODE>                    mode [choices: fast, slow]
"""

    @dataclass
    class Cmd:
        mode: str = arg("", positional=True)

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_bash(cmd)

    # Should have choices in completion
    assert "fast slow" in result


def test_bash_subcommand_with_options() -> None:
    """Test bash generates proper subcommand completions."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        verbose: bool = arg(False, short="-v")
        output: str = arg("", short="-o")

    def noop(_: object) -> int:
        return 0

    child_usage = """\
Child command.

Usage: parent child [OPTIONS]

Options:
  -v, --verbose             verbose mode
  -o, --output <FILE>       output file
"""
    child = Command("child", Child, noop, child_usage)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_bash(parent)

    # Should have subcommand function
    assert "_parent_child()" in result
    # Should have flags in subcommand
    assert "--verbose" in result
    assert "--output" in result


def test_zsh_with_choices_option() -> None:
    """Test zsh completion with choices on same line."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
      --mode <MODE>         mode [choices: fast, slow]
"""

    @dataclass
    class Cmd:
        mode: str = arg("")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_zsh(cmd)

    # Should have choices spec
    assert "(fast slow)" in result


def test_zsh_with_directory_option() -> None:
    """Test zsh completion with directory option."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
      --dir <DIR>           directory path
"""

    @dataclass
    class Cmd:
        dir: str = arg("")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_zsh(cmd)

    # Should have directory completion
    assert ":directory:_files -/" in result


def test_zsh_subcommand_with_choices() -> None:
    """Test zsh subcommand with choices option."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        mode: str = arg("")

    def noop(_: object) -> int:
        return 0

    child_usage = """\
Child command.

Usage: parent child [OPTIONS]

Options:
      --mode <MODE>         mode [choices: fast, slow]
"""
    child = Command("child", Child, noop, child_usage)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_zsh(parent)

    # Should have choices in subcommand function
    assert "(fast slow)" in result


def test_zsh_subcommand_with_directory() -> None:
    """Test zsh subcommand with directory option."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        dir: str = arg("")

    def noop(_: object) -> int:
        return 0

    child_usage = """\
Child command.

Usage: parent child [OPTIONS]

Options:
      --dir <DIR>           directory path
"""
    child = Command("child", Child, noop, child_usage)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_zsh(parent)

    # Should have directory completion in subcommand
    assert ":directory:_files -/" in result


def test_fish_with_choices_option() -> None:
    """Test fish completion with choices option."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
      --mode <MODE>         mode [choices: fast, slow]
"""

    @dataclass
    class Cmd:
        mode: str = arg("")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_fish(cmd)

    # Should have choices
    assert "-a 'fast slow'" in result


def test_fish_with_directory_option() -> None:
    """Test fish completion with directory option."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
      --dir <DIR>           directory path
"""

    @dataclass
    class Cmd:
        dir: str = arg("")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_fish(cmd)

    # Should have directory completion
    assert "__fish_complete_directories" in result


def test_fish_nested_subcommands() -> None:
    """Test fish with nested subcommands."""

    @dataclass
    class Root:
        pass

    @dataclass
    class Sub:
        pass

    @dataclass
    class SubSub:
        """Nested subcommand."""

        pass

    def noop(_: object) -> int:
        return 0

    subsub = Command("subsub", SubSub, noop)
    sub = Command("sub", Sub, noop, subcommands={"subsub": subsub})
    root = Command("root", Root, noop, subcommands={"sub": sub})

    result = completions.generate_fish(root)

    # Should have nested subcommand completion
    assert "-a 'sub'" in result
    assert "-a 'subsub'" in result


def test_run_with_exception(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test run() handles exceptions."""
    from cosmofy import completions as comp_module

    def raise_error(*args: object, **kwargs: object) -> str:
        raise ValueError("test error")

    monkeypatch.setattr(comp_module, "generate_completions", raise_error)

    args = completions.Args(shell="bash")  # type: ignore[arg-type]
    result = completions.run(args)

    assert result == 1


def test_bash_no_value_flags() -> None:
    """Test bash completion when no flags take values."""
    usage = """\
Usage: cmd [OPTIONS]

Options:
  -v, --verbose             verbose mode
  -q, --quiet               quiet mode
"""

    @dataclass
    class Cmd:
        verbose: bool = arg(False, short="-v")
        quiet: bool = arg(False, short="-q")

    def noop(_: object) -> int:
        return 0

    cmd = Command("cmd", Cmd, noop, usage)
    result = completions.generate_bash(cmd)

    # Should not have "case $prev in" since no flags take values
    # But should still have flag completions
    assert "_cmd_completions()" in result
    assert "--verbose" in result
    assert "--quiet" in result


def test_fish_subcommand_with_choices() -> None:
    """Test fish completion with subcommand that has choices option."""

    @dataclass
    class Parent:
        pass

    @dataclass
    class Child:
        mode: str = arg("")

    def noop(_: object) -> int:
        return 0

    child_usage = """\
Child command.

Usage: parent child [OPTIONS]

Options:
      --mode <MODE>         mode [choices: fast, slow]
"""
    child = Command("child", Child, noop, child_usage)
    parent = Command("parent", Parent, noop, subcommands={"child": child})

    result = completions.generate_fish(parent)

    # Should have choices in subcommand completions
    assert "__fish_seen_subcommand_from child" in result
    assert "-a 'fast slow'" in result
