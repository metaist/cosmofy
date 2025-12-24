"""baton: Dataclass argument parser with subcommand handoff."""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from dataclasses import Field
from dataclasses import fields
from dataclasses import MISSING
from dataclasses import replace
from os import environ as ENV
from textwrap import dedent
from types import UnionType
from typing import Any
from typing import Callable
from typing import cast
from typing import get_args
from typing import get_origin
from typing import get_type_hints
from typing import Literal
from typing import TextIO
from typing import Union
import logging
import re
import sys

# TODO py3.10
if sys.version_info >= (3, 11):  # pragma: no cover
    from typing import assert_never
else:  # pragma: no cover

    def assert_never(arg: Any, /) -> None:
        value = repr(arg)
        raise AssertionError(f"Expected code to be unreachable, but got: {value}")


Action = Literal[
    "",
    "store",
    "store_bool",
    "store_true",
    "store_false",
    "append",
    "extend",
    "count",
]


@dataclass
class ArgMetadata:
    short: str = ""
    action: Action = ""  # infer, by default
    required: bool = False
    positional: bool = False
    env: str = ""


def arg(
    default: Any,
    *,
    short: str = "",
    env: str = "",
    positional: bool = False,
    required: bool = False,
    action: Action = "",
    **kwargs: Any,
) -> Any:
    """`dataclasses.field` wrapper for argument metadata."""
    if required and not positional:
        raise ValueError("optional arguments cannot be required")

    metadata = kwargs.pop("metadata", {})
    metadata["arg"] = ArgMetadata(
        short=short,
        action=action,
        required=required,
        positional=positional,
        env=env,
    )
    if "default_factory" not in kwargs:  # can't set both
        if default in (list, dict, set):
            kwargs["default_factory"] = default
        else:
            kwargs["default"] = default
    return field(metadata=metadata, **kwargs)


def get_choices(kind: Any) -> tuple[type, list[Any]] | None:
    """Extract choices from Literal type, if present."""
    if get_origin(kind) is Literal:
        choices = get_args(kind)
        # infer item type from first choice
        item_type = type(choices[0]) if choices else str
        return cast(type, item_type), list(choices)
    return None


def get_item_type(kind: type | UnionType) -> type:
    """Get the item type for list[X] -> X, else return kind."""
    origin = get_origin(kind)
    if origin in (list, Union, UnionType):
        args = get_args(kind)
        return cast(type, args[0]) if args else str
    return cast(type, kind)


def infer_action(kind: type, positional: bool = False) -> Action:
    """Infer action from type and default value."""
    origin = getattr(kind, "__origin__", None)
    if origin is list:
        return "extend"
    if kind is bool:
        return "store_bool" if positional else "store_true"
    return "store"


@dataclass
class Arg:
    long: str
    short: str
    field_name: str
    field_type: type
    item_type: type  # for containers, otherwise same as field_type
    choices: list[Any]
    action: Action
    required: bool
    positional: bool
    env: str

    @staticmethod
    def from_class(spec: type) -> list[Arg]:
        """Return list of arguments from a class."""
        hints = get_type_hints(spec)
        return [Arg.from_field(f, hints) for f in fields(spec)]

    @classmethod
    def from_field(cls, f: Field[Any], type_hints: dict[str, type]) -> Arg:
        """Return an argument constructed from a field."""
        kind = type_hints.get(f.name, str)
        if choices_info := get_choices(kind):
            item_type, choices = choices_info
        else:
            item_type = get_item_type(kind)
            choices = []

        meta: ArgMetadata | None = f.metadata.get("arg")
        if meta is not None:
            action = meta.action or infer_action(kind, meta.positional)
            short = meta.short
            required = meta.required
            positional = meta.positional
            env = meta.env
        else:  # need to infer
            action = infer_action(kind)
            short = ""
            required = f.default is MISSING
            positional = False
            env = ""

        return cls(
            long=f.name if positional else f"--{f.name.replace('_', '-')}",
            short=short,
            env=env,
            field_name=f.name,
            field_type=kind,
            item_type=item_type,
            choices=choices,
            action=action,
            positional=positional,
            required=required,
        )


def _init_context(cmd: Command, parent: Any | None) -> object:
    """Create context with appropriate defaults."""
    ctx = cmd.cls()

    for spec in cmd.args:
        if spec.env and spec.env in ENV:
            val = ENV[spec.env]
            if spec.action in ("store_true", "store_false"):
                _do_action(ctx, replace(spec, action="store_bool"), val)
            else:
                _do_action(ctx, spec, val)
    # env defaults set

    if parent:
        parent_fields = {f.name for f in fields(parent)}
        for f in fields(cmd.cls):
            if f.name in parent_fields:
                setattr(ctx, f.name, getattr(parent, f.name))
    # parent parsed values set

    return ctx


def _pop_values(argv: list[str], stop: set[str] | None = None) -> list[str]:
    """Pop values from argv until a flag or stop condition."""
    stop = stop or set()
    vals = []
    while argv and not argv[0].startswith("-") and argv[0] not in stop:
        vals.append(argv.pop(0))
    return vals


def _do_action(ctx: object, spec: Arg, val: str | list[str] = "") -> None:
    """Apply a parsed value to the context object."""
    name = spec.field_name
    kind = spec.item_type
    match spec.action:
        case "store":
            if spec.choices and val not in spec.choices:
                err = f"invalid value '{val}' for {spec.long}"
                err += f"\n  [choices: {', '.join(spec.choices)}]"
                raise ValueError(err)
            setattr(ctx, name, kind(val))
        case "store_bool":
            assert isinstance(val, str)
            setattr(ctx, name, val.lower() in ("1", "true", "yes", "on", "y", "t"))
        case "store_true":
            setattr(ctx, name, True)
        case "store_false":
            setattr(ctx, name, False)
        case "append":
            getattr(ctx, name).append(kind(val))
        case "extend":
            getattr(ctx, name).extend(kind(v) for v in val)
        case "count":
            setattr(ctx, name, getattr(ctx, name) + 1)
        case _:  # pragma: no cover
            assert_never(spec.action)


def _parse_optional(ctx: object, spec: Arg, argv: list[str]) -> None:
    """Parse an optional argument, consuming values from argv."""
    match spec.action:
        case "count" | "store_true" | "store_false":
            _do_action(ctx, spec, "")
        case "store" | "store_bool" | "append":
            if not argv:
                err = f"a value is required for {spec.long}, but none was supplied"
                if spec.choices:
                    err += f"\n  [choices: {', '.join(spec.choices)}]"
                raise ValueError(err)
            _do_action(ctx, spec, argv.pop(0))
        case "extend":
            vals = _pop_values(argv)
            if not vals:
                err = f"a value is required for {spec.long}, but none was supplied"
                if spec.choices:
                    err += f"\n  [choices: {', '.join(spec.choices)}]"
                raise ValueError(err)
            _do_action(ctx, spec, vals)
        case _:  # pragma: no cover
            assert_never(spec.action)


def _parse(
    cmd: Command, argv: list[str], parent: Any | None = None
) -> tuple[Any, Command | None, list[str]]:
    """Parse `argv` into `cmd.cls` instance.

    Returns: (parsed_args, subcommand_name | None, remaining_argv)
    """
    ctx = _init_context(cmd, parent)
    aliases = cmd.aliases
    optionals = cmd.optionals
    positionals = list(cmd.positionals)
    subcommand: Command | None = None

    while argv:
        val = argv.pop(0)

        # Handle --foo=bar
        if "=" in val and val.startswith("-"):
            val, rest = val.split("=", 1)
            argv.insert(0, rest)

        # Rest are positional
        if val == "--":
            if positionals and positionals[0].action == "extend":
                _do_action(ctx, positionals.pop(0), argv.copy())
            elif positionals:
                for v in argv:
                    if not positionals:
                        raise ValueError(f"unexpected argument: '{v}'")
                    _do_action(ctx, positionals.pop(0), v)
            elif argv:
                raise ValueError(f"unexpected argument: '{argv[0]}'")
            argv = []
            break

        # Expand -vvv -> --verbose --verbose --verbose
        if val.startswith("-") and not val.startswith("--") and " " not in val:
            expanded = []
            for c in val[1:]:
                if alias := aliases.get(f"-{c}"):
                    expanded.append(alias)
                else:
                    raise ValueError(f"unknown option: '-{c}'")
            argv = expanded + argv
            continue

        # Optional
        if val.startswith("--") and " " not in val:
            spec = optionals.get(val)
            if not spec:
                raise ValueError(f"unknown option: '{val}'")
            _parse_optional(ctx, spec, argv)
            continue

        # Positional
        if not positionals:
            raise ValueError(f"unexpected argument: '{val}'")

        spec = positionals.pop(0)
        # TODO: Mark the positional that is supposed to receive the subcommand name.
        if spec.long == "command" and val not in cmd.subcommands:
            raise ValueError(f"unknown subcommand name: '{val}'")

        if spec.action == "extend":
            vals = [val] + _pop_values(argv, set(cmd.subcommands.keys()))
            _do_action(ctx, spec, vals)
        else:
            _do_action(ctx, spec, val)

        # Subcommand
        if val in cmd.subcommands:
            subcommand = cmd.subcommands[val]
            break

    # Check required
    missing = [f"<{s.field_name.upper()}>" for s in positionals if s.required]
    if missing and not getattr(ctx, "help", None):
        s = "s" if len(missing) > 1 else ""
        raise ValueError(f"missing required argument{s}: {', '.join(missing)}")

    return ctx, subcommand, argv


def parse(cls: Any, argv: list[str]) -> Any:
    """Parse `argv` into an instance of `cls` without any subcommands."""
    cmd = Command(cls.__name__, cls, lambda _: 0)
    ctx, _, _ = _parse(cmd, argv)
    return ctx


@dataclass
class Command:
    name: str
    cls: type  # The dataclass for args
    run: Callable[[Any], int]  # Takes parsed args, returns exit code
    usage: str = ""
    subcommands: dict[str, Command] = field(default_factory=dict)

    _args: list[Arg] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Make some adjustments after the dataclass is built."""
        self._args = Arg.from_class(self.cls)
        if not self.usage:
            self.usage = dedent(self.cls.__doc__ or "")

    @property
    def args(self) -> list[Arg]:
        """Return the current args."""
        return self._args

    @property
    def aliases(self) -> dict[str, str]:
        """Return argument aliases mapped to their long counter-parts."""
        return {a.short: a.long for a in self._args if a.short}

    @property
    def optionals(self) -> dict[str, Arg]:
        """Return optional arguments."""
        return {a.long: a for a in self._args if not a.positional}

    @property
    def positionals(self) -> list[Arg]:
        """Return list of positional arguments."""
        return [a for a in self._args if a.positional]

    def show_usage(self, *, short: bool = False, color: COLOR_MODE = "auto") -> None:
        """Display the usage for this command."""
        usage = self.usage
        if short:
            beg = usage.find("Usage:")
            end: int | None = usage.find("\n\n", beg)
            if end == -1:
                end = None  # go to the end
            usage = f"\n{usage[beg:end]}\n\nFor more information, try --help."
        else:
            usage = self.usage.strip()
        if use_color(color, sys.stdout):
            usage = decorate(usage)
        print(render_tags(usage, color=color))

    parse = _parse

    def main(
        self: Command, argv: list[str] | None = None, parent: object | None = None
    ) -> int:
        """Parse and execute the command."""
        log = logging.getLogger(self.name)
        if argv is None:
            argv = sys.argv[1:]

        try:
            args, sub, remaining = _parse(self, argv, parent)
            if getattr(args, "help", False):
                self.show_usage(color=getattr(args, "color", "auto"))
                return 0

            if sub:
                return sub.main(remaining, parent=args)
            return self.run(args)
        except ValueError as e:
            log.error(e)
            self.show_usage(short=True)
            return 1


COLOR_MODE = Literal["auto", "always", "never"]
COLOR_CODE: dict[str, str] = {
    "reset": "0",
    "bold": "1",
    "dim": "2",
    "italic": "3",
    "underline": "4",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
}

DEFAULT_THEME = {
    "heading": "bold green",  # Heading:
    "command": "bold cyan",  # command
    "argument": "cyan",  # <ARGUMENT>
    "option": "cyan",  # [OPTION]
    "flag": "bold cyan",  # --flag
    "repeats": "cyan",  # ...
    "tick": "bold white",  # `tick`
    "string": "yellow",  # 'yellow'
    "choice": "green",  # [choices: a, b, c]
    "default": "yellow",  # [default: value]
    "env": "white",  # [env: NAME=value]
    "tip": "green",  # tip:
}


class ColorFormatter(logging.Formatter):
    """Log formatter that renders [tag]...[/] markup to ANSI colors."""

    color: COLOR_MODE
    _stream: TextIO | None

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        *,
        color: COLOR_MODE = "auto",
    ):
        """Construct a new `ColorFormatter`."""
        super().__init__(fmt, datefmt, style)
        self.color = color
        self._stream = None  # check at format time

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        match record.levelname:
            case "ERROR":
                level = "[bold red]error[/]"
            case "WARNING":
                level = "[bold yellow]warning[/]"
            case "INFO":
                level = "[bold cyan]info[/]"
            case "DEBUG":
                level = "[dim]debug[/]"
            case _:
                level = record.levelname.lower()

        record.levelname = level
        message = super().format(record)
        stream = self._stream or sys.stderr
        if self.color in ("auto", "always"):
            message = decorate(message)
        return render_tags(message, color=self.color, file=stream)

    def set_stream(self, stream: TextIO) -> None:
        """Set the stream for TTY detection (called by handler)."""
        self._stream = stream


class ColorHandler(logging.StreamHandler):  # type: ignore
    """StreamHandler that automatically configures ColorFormatter's stream.

    Usage:
        import logging
        from baton import ColorHandler

        handler = ColorHandler()
        handler.setFormatter(ColorFormatter("[dim]%(asctime)s[/] %(message)s"))
        logging.getLogger().addHandler(handler)
    """

    def setFormatter(self, fmt: logging.Formatter | None) -> None:
        """Set the formatter."""
        super().setFormatter(fmt)
        if isinstance(fmt, ColorFormatter):
            fmt.set_stream(self.stream)


def use_color(color: COLOR_MODE, file: Any) -> bool:
    """Return `True` if we should output ANSI color codes."""
    # See: https://no-color.org/
    # See: https://bixense.com/clicolors/

    # cli
    if color == "never":
        return False
    if color == "always":
        return True

    # env
    if ENV.get("NO_COLOR") or ENV.get("CLICOLOR") in ["0", "false"]:
        return False
    if ENV.get("FORCE_COLOR") or ENV.get("CLICOLOR_FORCE"):
        return True

    # auto
    if not hasattr(file, "isatty") or not file.isatty():
        return False
    return ENV.get("TERM", "") != "dumb"


def render_tags(
    text: str,
    *,
    color: COLOR_MODE = "auto",
    file: Any | None = None,
    theme: dict[str, str] | None = None,
) -> str:
    """Render [tag]...[/] markup to ANSI (or strip if no color)."""
    if theme is None:
        theme = DEFAULT_THEME

    def replace_tag(m: re.Match[str]) -> str:
        """Return the string with the tag replaced."""
        tag = m.group(1).lower()
        if tag == "/":
            tag = "reset"
        tag = theme.get(tag, tag)
        parts = tag.split()
        codes = [COLOR_CODE[p] for p in parts if p in COLOR_CODE]
        if codes:
            return f'\033[{";".join(codes)}m'
        return m.group(0)  # Unknown tag, leave as-is

    if use_color(color, sys.stdout if file is None else file):
        return re.sub(r"\[([^[\]]+)\]", replace_tag, text)
    else:
        return re.sub(r"\[/?[a-z ]*\]", "", text)


def decorate(text: str) -> str:
    """Apply theme markings."""
    result = text

    # Usage: command
    # starts with usage and everything up to the first non lowercase word
    result = re.sub(r"Usage: ([a-z ]+)", r"Usage: [command]\1[/]", result)

    # Heading:
    # start of a line, starts with a capital letter ends with a colon
    result = re.sub(r"\n([A-Z][^\n:]+:)", r"\n[heading]\1[/]", result)

    # command
    # two spaces before and after, all lowercase, can have dashes
    result = re.sub(r"  ([a-z][-_a-z]+)  ", r"  [command]\1[/]  ", result)

    # [OPTION], [OPTION...]
    result = re.sub(r"\[([<A-Z_>]+)\]", r"[option][\1][/]", result)

    # <ARGUMENT>
    result = re.sub(r"<([A-Z_]+)>", r"[argument]<\1>[/]", result)

    # `--flag`, --flag
    result = re.sub(r"`(-[-A-Za-z]+)`", r"[flag]\1[/]", result)
    result = re.sub(r"(\s+)(-[-A-Za-z]+)", r"\1[flag]\2[/]", result)

    # `tick`
    result = re.sub(r"`([^`]+)`", r"[tick]\1[/]", result)

    # 'string'
    result = re.sub(r"'([^']+)'", r"'[string]\1[/]'", result)

    # repeats
    result = re.sub(r"([a-z\]>])(\.\.\.)", r"\1[repeats]\2[/]", result)

    # tip:
    result = re.sub(r"  tip:", r"  [tip]tip:[/]", result)

    # [default: value]
    result = re.sub(r"\[default: ([^\]]+)\]", r"[default: [default]\1[/]]", result)

    # [env: NAME=value]
    result = re.sub(
        r"\[env: ([^=]+)=([^\]]*)\]", r"[env: [env]\1[/]=[default]\2[/]]", result
    )

    # [choices: a, b, c]
    result = re.sub(
        r"\[(choices|possible values):\s*([^\]]+)\]",
        lambda m: f"[{m.group(1)}: "
        + re.sub(
            r"\s*,\s*",
            ", ",
            re.sub(r"\s*([^,\]]+)\s*", r"[choice]\1[/]", m.group(2)).strip(),
        )
        + "]",
        result,
    )

    return result
