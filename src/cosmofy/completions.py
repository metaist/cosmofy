#!/usr/bin/env python
"""Generate shell completions from usage strings."""

# std
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import logging
import re
import sys

# pkg
from .args import global_options
from .args import GlobalArgs
from .baton import arg
from .baton import Command

log = logging.getLogger(__name__)

Shell = Literal["bash", "zsh", "fish"]

# Map placeholder names to completion types
PLACEHOLDER_COMPLETIONS: dict[str, str] = {
    "FILE": "file",
    "PATH": "file",
    "BUNDLE": "file",
    "SCRIPT": "file",
    "DIR": "directory",
    "DIRECTORY": "directory",
    "COMMAND": "subcommand",
    "SHELL": "choices",  # will use explicit choices
}


@dataclass
class FlagInfo:
    """Information about a flag/option parsed from usage."""

    short: str  # e.g., "-a"
    long: str  # e.g., "--all"
    takes_value: bool  # whether it needs an argument
    placeholder: str  # e.g., "FILE" for --output <FILE>
    choices: list[str]  # explicit choices if any
    description: str  # help text


@dataclass
class PositionalInfo:
    """Information about a positional argument parsed from usage."""

    name: str  # e.g., "BUNDLE"
    required: bool  # <BUNDLE> vs [BUNDLE]
    repeatable: bool  # ends with ...
    choices: list[str]  # explicit choices if any


def parse_flags(usage: str) -> list[FlagInfo]:
    """Parse flags and options from usage string."""
    flags: list[FlagInfo] = []

    # Match lines like:
    #   -a, --all                 description
    #   --flag                    description
    #   -o, --output <FILE>       description
    #       --sort <MODE>         [choices: a, b, c]
    pattern = re.compile(
        r"^\s+"  # leading whitespace
        r"(?:(-[a-zA-Z]),?\s*)?"  # optional short flag
        r"(--[\w-]+)"  # long flag (required)
        r"(?:\s+<(\w+)>)?"  # optional placeholder
        r"\s{2,}"  # gap before description
        r"(.*)$",  # description (may span lines)
        re.MULTILINE,
    )

    for match in pattern.finditer(usage):
        short = match.group(1) or ""
        long = match.group(2)
        placeholder = match.group(3) or ""
        desc_line = match.group(4)

        # Check for choices in description or following lines
        choices: list[str] = []
        choices_match = re.search(r"\[choices:\s*([^\]]+)\]", desc_line)
        if choices_match:
            choices = [c.strip() for c in choices_match.group(1).split(",")]

        # Clean description
        description = re.sub(r"\[(?:choices|default|env):[^\]]+\]", "", desc_line)
        description = description.strip()

        flags.append(
            FlagInfo(
                short=short,
                long=long,
                takes_value=bool(placeholder),
                placeholder=placeholder,
                choices=choices,
                description=description,
            )
        )

    return flags


def parse_positionals(usage: str) -> list[PositionalInfo]:
    """Parse positional arguments from Usage: line and Arguments: section."""
    positionals: list[PositionalInfo] = []

    # Parse the Usage: line for positional structure
    usage_line_match = re.search(r"Usage:\s*[^\n]+", usage)
    if not usage_line_match:
        return positionals

    usage_line = usage_line_match.group(0)

    # Find positionals: <NAME>, [NAME], <NAME>..., [NAME]...
    # Skip [OPTIONS] which is not a real positional
    pos_pattern = re.compile(r"([<\[])([A-Z_]+)(\.\.\.)?[\]>]")
    for match in pos_pattern.finditer(usage_line):
        bracket = match.group(1)
        name = match.group(2)
        dots = match.group(3)

        if name == "OPTIONS":
            continue

        positionals.append(
            PositionalInfo(
                name=name,
                required=bracket == "<",
                repeatable=bool(dots),
                choices=[],
            )
        )

    # Look for choices in Arguments: section
    args_section = re.search(
        r"Arguments:.*?(?=\n\n|\n[A-Z]|\Z)", usage, re.DOTALL | re.IGNORECASE
    )
    if args_section:
        for pos in positionals:
            # Find description line for this positional
            pattern = rf"[<\[]{pos.name}[>\]].*?\[choices:\s*([^\]]+)\]"
            choices_match = re.search(pattern, args_section.group(0), re.IGNORECASE)
            if choices_match:
                pos.choices = [c.strip() for c in choices_match.group(1).split(",")]

    return positionals


def get_subcommands(cmd: Command) -> dict[str, str]:
    """Extract subcommand names and descriptions from a Command."""
    result: dict[str, str] = {}
    for name, subcmd in cmd.subcommands.items():
        # Get first line of usage as description
        desc = subcmd.usage.split("\n")[0].strip() if subcmd.usage else ""
        result[name] = desc
    return result


def get_completion_type(placeholder: str, choices: list[str]) -> str:
    """Determine completion type from placeholder name and choices."""
    if choices:
        return "choices"
    return PLACEHOLDER_COMPLETIONS.get(placeholder.upper(), "none")


def generate_bash(cmd: Command) -> str:
    """Generate bash completion script."""
    name = cmd.name.replace(".", "-")
    root_name = name.split("-")[0] if "-" in name else name

    flags = parse_flags(cmd.usage)
    positionals = parse_positionals(cmd.usage)
    subcommands = get_subcommands(cmd)

    lines = [
        f"# Bash completion for {root_name}",
        "# Generated from usage strings",
        "",
        f"_{root_name}_completions() {{",
        "    local cur prev words cword",
        "    _init_completion || return",
        "",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        '    prev="${COMP_WORDS[COMP_CWORD-1]}"',
        "",
    ]

    # Handle previous word (option that takes a value)
    if flags:
        lines.append("    # Handle options that take values")
        lines.append("    case $prev in")
        for flag in flags:
            if flag.takes_value:
                flag_patterns = [flag.long]
                if flag.short:
                    flag_patterns.append(flag.short)
                pattern = "|".join(flag_patterns)

                comp_type = get_completion_type(flag.placeholder, flag.choices)
                if comp_type == "choices" and flag.choices:
                    choices_str = " ".join(flag.choices)
                    lines.append(f"        {pattern})")
                    lines.append(
                        f'            COMPREPLY=($(compgen -W "{choices_str}" -- "$cur"))'
                    )
                    lines.append("            return")
                    lines.append("            ;;")
                elif comp_type == "file":
                    lines.append(f"        {pattern})")
                    lines.append("            _filedir")
                    lines.append("            return")
                    lines.append("            ;;")
                elif comp_type == "directory":
                    lines.append(f"        {pattern})")
                    lines.append("            _filedir -d")
                    lines.append("            return")
                    lines.append("            ;;")
        lines.append("    esac")
        lines.append("")

    # Handle current word
    lines.append("    # Handle current word")
    lines.append("    case $cur in")
    lines.append("        -*)")

    # All flags
    all_flags: list[str] = []
    for flag in flags:
        all_flags.append(flag.long)
        if flag.short:
            all_flags.append(flag.short)
    flags_str = " ".join(all_flags)
    lines.append(f'            COMPREPLY=($(compgen -W "{flags_str}" -- "$cur"))')
    lines.append("            ;;")

    # Default case - subcommands or files
    lines.append("        *)")
    if subcommands:
        subcmd_str = " ".join(subcommands.keys())
        lines.append(f'            COMPREPLY=($(compgen -W "{subcmd_str}" -- "$cur"))')
    else:
        # Check positionals for file/directory completion
        for pos in positionals:
            comp_type = get_completion_type(pos.name, pos.choices)
            if comp_type == "file":
                lines.append("            _filedir")
                break
            elif comp_type == "directory":
                lines.append("            _filedir -d")
                break
            elif comp_type == "choices" and pos.choices:
                choices_str = " ".join(pos.choices)
                lines.append(
                    f'            COMPREPLY=($(compgen -W "{choices_str}" -- "$cur"))'
                )
                break
        else:
            lines.append("            _filedir")
    lines.append("            ;;")
    lines.append("    esac")
    lines.append("}")
    lines.append("")
    lines.append(f"complete -F _{root_name}_completions {root_name}")

    # Generate completions for subcommands recursively
    for subcmd_name, subcmd in cmd.subcommands.items():
        lines.append("")
        lines.extend(_generate_bash_subcommand(root_name, [subcmd_name], subcmd))

    return "\n".join(lines)


def _generate_bash_subcommand(
    root_name: str, path: list[str], cmd: Command
) -> list[str]:
    """Generate bash completion for a subcommand."""
    func_name = f"_{root_name}_{'_'.join(path)}"
    flags = parse_flags(cmd.usage)
    subcommands = get_subcommands(cmd)

    lines = [
        f"{func_name}() {{",
        "    local cur prev",
        "    _init_completion || return",
        "",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        '    prev="${COMP_WORDS[COMP_CWORD-1]}"',
        "",
    ]

    # Handle options that take values
    if flags:
        value_flags = [f for f in flags if f.takes_value]
        if value_flags:
            lines.append("    case $prev in")
            for flag in value_flags:
                flag_patterns = [flag.long]
                if flag.short:
                    flag_patterns.append(flag.short)
                pattern = "|".join(flag_patterns)

                comp_type = get_completion_type(flag.placeholder, flag.choices)
                if comp_type == "choices" and flag.choices:
                    choices_str = " ".join(flag.choices)
                    lines.append(f"        {pattern})")
                    lines.append(
                        f'            COMPREPLY=($(compgen -W "{choices_str}" -- "$cur"))'
                    )
                    lines.append("            return")
                    lines.append("            ;;")
                elif comp_type == "file":
                    lines.append(f"        {pattern})")
                    lines.append("            _filedir")
                    lines.append("            return")
                    lines.append("            ;;")
                elif comp_type == "directory":
                    lines.append(f"        {pattern})")
                    lines.append("            _filedir -d")
                    lines.append("            return")
                    lines.append("            ;;")
            lines.append("    esac")
            lines.append("")

    # Handle current word
    lines.append("    case $cur in")
    lines.append("        -*)")

    all_flags: list[str] = []
    for flag in flags:
        all_flags.append(flag.long)
        if flag.short:
            all_flags.append(flag.short)
    flags_str = " ".join(all_flags) if all_flags else ""
    if flags_str:
        lines.append(f'            COMPREPLY=($(compgen -W "{flags_str}" -- "$cur"))')
    lines.append("            ;;")

    lines.append("        *)")
    if subcommands:
        subcmd_str = " ".join(subcommands.keys())
        lines.append(f'            COMPREPLY=($(compgen -W "{subcmd_str}" -- "$cur"))')
    else:
        # Default to file completion
        lines.append("            _filedir")
    lines.append("            ;;")
    lines.append("    esac")
    lines.append("}")

    # Recurse for nested subcommands
    for subcmd_name, subcmd in cmd.subcommands.items():
        lines.append("")
        lines.extend(_generate_bash_subcommand(root_name, path + [subcmd_name], subcmd))

    return lines


def generate_zsh(cmd: Command) -> str:
    """Generate zsh completion script."""
    name = cmd.name.replace(".", "-")
    root_name = name.split("-")[0] if "-" in name else name

    flags = parse_flags(cmd.usage)
    subcommands = get_subcommands(cmd)

    lines = [
        f"#compdef {root_name}",
        f"# Zsh completion for {root_name}",
        "# Generated from usage strings",
        "",
        f"_{root_name}() {{",
        "    local -a opts args",
        "",
    ]

    # Define options
    if flags:
        lines.append("    opts=(")
        for flag in flags:
            desc = (
                flag.description.replace("'", "'\\''")
                .replace("[", "\\[")
                .replace("]", "\\]")
            )
            if flag.takes_value:
                comp_type = get_completion_type(flag.placeholder, flag.choices)
                if comp_type == "choices" and flag.choices:
                    choices_str = " ".join(flag.choices)
                    spec = f"({choices_str})"
                elif comp_type == "file":
                    spec = ":file:_files"
                elif comp_type == "directory":
                    spec = ":directory:_files -/"
                else:
                    spec = f":{flag.placeholder.lower()}:"

                if flag.short:
                    lines.append(f"        '{flag.short}[{desc}]{spec}'")
                lines.append(f"        '{flag.long}[{desc}]{spec}'")
            else:
                if flag.short:
                    lines.append(f"        '{flag.short}[{desc}]'")
                lines.append(f"        '{flag.long}[{desc}]'")
        lines.append("    )")
        lines.append("")

    # Define subcommands
    if subcommands:
        lines.append("    local -a subcmds")
        lines.append("    subcmds=(")
        for subcmd_name, desc in subcommands.items():
            desc_escaped = desc.replace("'", "'\\''").replace(":", "\\:")
            lines.append(f"        '{subcmd_name}:{desc_escaped}'")
        lines.append("    )")
        lines.append("")

    # Main completion logic
    lines.append("    _arguments -s \\")
    lines.append("        $opts \\")
    if subcommands:
        lines.append("        '1:command:->subcmd' \\")
        lines.append("        '*::arg:->args'")
        lines.append("")
        lines.append("    case $state in")
        lines.append("        subcmd)")
        lines.append("            _describe 'command' subcmds")
        lines.append("            ;;")
        lines.append("        args)")
        lines.append("            case $words[1] in")
        for subcmd_name in subcommands:
            lines.append(f"                {subcmd_name})")
            lines.append(f"                    _{root_name}_{subcmd_name}")
            lines.append("                    ;;")
        lines.append("            esac")
        lines.append("            ;;")
        lines.append("    esac")
    else:
        lines.append("        '*:file:_files'")

    lines.append("}")
    lines.append("")

    # Generate subcommand functions
    for subcmd_name, subcmd in cmd.subcommands.items():
        lines.extend(_generate_zsh_subcommand(root_name, subcmd_name, subcmd))
        lines.append("")

    lines.append(f"_{root_name}")
    return "\n".join(lines)


def _generate_zsh_subcommand(
    root_name: str, subcmd_name: str, cmd: Command
) -> list[str]:
    """Generate zsh completion function for a subcommand."""
    func_name = f"_{root_name}_{subcmd_name}"
    flags = parse_flags(cmd.usage)
    subcommands = get_subcommands(cmd)

    lines = [f"{func_name}() {{"]

    if flags:
        lines.append("    local -a opts")
        lines.append("    opts=(")
        for flag in flags:
            desc = (
                flag.description.replace("'", "'\\''")
                .replace("[", "\\[")
                .replace("]", "\\]")
            )
            if flag.takes_value:
                comp_type = get_completion_type(flag.placeholder, flag.choices)
                if comp_type == "choices" and flag.choices:
                    choices_str = " ".join(flag.choices)
                    spec = f"({choices_str})"
                elif comp_type == "file":
                    spec = ":file:_files"
                elif comp_type == "directory":
                    spec = ":directory:_files -/"
                else:
                    spec = f":{flag.placeholder.lower()}:"
                lines.append(f"        '{flag.long}[{desc}]{spec}'")
            else:
                lines.append(f"        '{flag.long}[{desc}]'")
        lines.append("    )")
        lines.append("")

    if subcommands:
        lines.append("    local -a subcmds")
        lines.append("    subcmds=(")
        for name, desc in subcommands.items():
            desc_escaped = desc.replace("'", "'\\''").replace(":", "\\:")
            lines.append(f"        '{name}:{desc_escaped}'")
        lines.append("    )")
        lines.append("")
        lines.append("    _arguments -s $opts '1:command:->subcmd' '*::arg:->args'")
        lines.append("    case $state in")
        lines.append("        subcmd) _describe 'command' subcmds ;;")
        lines.append("    esac")
    else:
        lines.append("    _arguments -s $opts '*:file:_files'")

    lines.append("}")
    return lines


def generate_fish(cmd: Command) -> str:
    """Generate fish completion script."""
    name = cmd.name.replace(".", "-")
    root_name = name.split("-")[0] if "-" in name else name

    flags = parse_flags(cmd.usage)
    subcommands = get_subcommands(cmd)

    lines = [
        f"# Fish completion for {root_name}",
        "# Generated from usage strings",
        "",
    ]

    # Disable file completion by default if we have subcommands
    if subcommands:
        lines.append(f"complete -c {root_name} -f")
        lines.append("")

    # Add flag completions
    for flag in flags:
        parts = [f"complete -c {root_name}"]

        if flag.short:
            parts.append(f"-s {flag.short[1:]}")  # remove leading -
        if flag.long:
            parts.append(f"-l {flag.long[2:]}")  # remove leading --

        if flag.description:
            desc = flag.description.replace("'", "\\'")
            parts.append(f"-d '{desc}'")

        if flag.takes_value:
            comp_type = get_completion_type(flag.placeholder, flag.choices)
            if comp_type == "choices" and flag.choices:
                parts.append("-r")  # requires argument
                parts.append(f"-a '{' '.join(flag.choices)}'")
            elif comp_type == "file":
                parts.append("-r -F")  # requires argument, file completion
            elif comp_type == "directory":
                parts.append("-r -a '(__fish_complete_directories)'")
            else:
                parts.append("-r")  # requires argument

        lines.append(" ".join(parts))

    lines.append("")

    # Add subcommand completions
    if subcommands:
        lines.append("# Subcommands")
        for subcmd_name, desc in subcommands.items():
            desc_escaped = desc.replace("'", "\\'")
            lines.append(
                f"complete -c {root_name} -n '__fish_use_subcommand' "
                f"-a '{subcmd_name}' -d '{desc_escaped}'"
            )

        # Generate completions for each subcommand
        lines.append("")
        for subcmd_name, subcmd in cmd.subcommands.items():
            lines.extend(_generate_fish_subcommand(root_name, subcmd_name, subcmd))

    return "\n".join(lines)


def _generate_fish_subcommand(
    root_name: str, subcmd_name: str, cmd: Command
) -> list[str]:
    """Generate fish completion for a subcommand."""
    lines = [f"# {root_name} {subcmd_name}"]

    flags = parse_flags(cmd.usage)
    subcommands = get_subcommands(cmd)

    cond = f"__fish_seen_subcommand_from {subcmd_name}"

    for flag in flags:
        parts = [f"complete -c {root_name} -n '{cond}'"]

        if flag.short:
            parts.append(f"-s {flag.short[1:]}")
        if flag.long:
            parts.append(f"-l {flag.long[2:]}")

        if flag.description:
            desc = flag.description.replace("'", "\\'")
            parts.append(f"-d '{desc}'")

        if flag.takes_value:
            comp_type = get_completion_type(flag.placeholder, flag.choices)
            if comp_type == "choices" and flag.choices:
                parts.append("-r")
                parts.append(f"-a '{' '.join(flag.choices)}'")
            elif comp_type == "file":
                parts.append("-r -F")
            else:
                parts.append("-r")

        lines.append(" ".join(parts))

    # Nested subcommands
    if subcommands:
        for name, desc in subcommands.items():
            desc_escaped = desc.replace("'", "\\'")
            lines.append(
                f"complete -c {root_name} -n '{cond}; and not __fish_seen_subcommand_from {' '.join(subcommands.keys())}' "
                f"-a '{name}' -d '{desc_escaped}'"
            )

    lines.append("")
    return lines


def generate_completions(cmd: Command, shell: Shell) -> str:
    """Generate completion script for the specified shell."""
    match shell:
        case "bash":
            return generate_bash(cmd)
        case "zsh":
            return generate_zsh(cmd)
        case "fish":
            return generate_fish(cmd)
        case _:  # pragma: no cover
            raise ValueError(f"unsupported shell: {shell}")


# --- Command interface ---

usage = f"""\
Generate shell completion scripts.

Usage: cosmofy completions <SHELL>

Arguments:
  <SHELL>                   shell to generate completions for
                            [choices: bash, zsh, fish]

{global_options}

Examples:
  # Bash (add to ~/.bashrc)
  eval "$(cosmofy completions bash)"

  # Zsh (add to ~/.zshrc or save to fpath)
  cosmofy completions zsh > ~/.zfunc/_cosmofy

  # Fish
  cosmofy completions fish > ~/.config/fish/completions/cosmofy.fish
"""


@dataclass
class Args(GlobalArgs):
    __doc__ = usage
    shell: Shell = arg("", positional=True, required=True)


def run(args: Args) -> int:
    """Entry point for `cosmofy completions`."""
    # Import here to avoid circular import
    from .__main__ import cmd as root_cmd

    args.setup_logger()
    try:
        output = generate_completions(root_cmd, args.shell)
        print(output)
    except Exception as e:
        args.show_error(log, e)
        return 1
    return 0


cmd = Command("cosmofy.completions", Args, run)

if __name__ == "__main__":  # pragma: no cover
    sys.exit(cmd.main())
