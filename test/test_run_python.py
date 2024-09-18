"""Test python CLI emulation within python."""

# std
from shlex import split
from unittest.mock import patch

# lib
import pytest

# pkg
from cosmofy.updater import main
from cosmofy.updater import PythonArgs
from cosmofy.updater import run_python


def test_parse() -> None:
    """Parse python CLI args."""
    # generic options
    assert PythonArgs.parse(split("")) == PythonArgs(i=True, argv=[""]), "no args = -i"
    assert PythonArgs.parse(split("-i")) == PythonArgs(i=True)
    assert PythonArgs.parse(split("-qi")) == PythonArgs(q=True, i=True)
    assert PythonArgs.parse(split("-V")) == PythonArgs(V=True)
    assert PythonArgs.parse(split("-VV")) == PythonArgs(V=True, VV=True)
    assert PythonArgs.parse(split("-V --version")) == PythonArgs(V=True, VV=True)
    assert PythonArgs.parse(split("--version --version")) == PythonArgs(V=True, VV=True)

    # interfaces: -c, -m, -, <script>
    assert PythonArgs.parse(split("-c 'f = 42' --extra")) == PythonArgs(
        c="f = 42", argv=["-c", "--extra"]
    )
    assert PythonArgs.parse(split("-m foo.bar --extra")) == PythonArgs(
        m="foo.bar", argv=["-m", "--extra"]
    )
    assert PythonArgs.parse(split("foo.py --extra")) == PythonArgs(
        script="foo.py", argv=["foo.py", "--extra"]
    )

    with patch("cosmofy.updater.sys.stdin") as _stdin:
        _stdin.read.return_value = "f = 42"
        _stdin.isatty.side_effect = [False, True]  # once as non-TTY, once as TTY
        assert PythonArgs.parse(split("-")) == PythonArgs(c="f = 42", argv=["-"])
        assert PythonArgs.parse(split("-")) == PythonArgs(
            c="f = 42", i=True, argv=["-"]
        )

    # missing args
    with pytest.raises(ValueError):
        PythonArgs.parse(split("-c"))

    with pytest.raises(ValueError):
        PythonArgs.parse(split("-m"))

    # invalid args
    with pytest.raises(ValueError):
        PythonArgs.parse(split("--fake"))

    # unsupported args
    with pytest.raises(ValueError):
        PythonArgs.parse(split("--help"))


def test_run() -> None:
    """Run python CLI."""
    assert run_python(split("--version")) == 0
    assert run_python(split("-VV")) == 0
    assert run_python(split("--fake")) == 2  # invalid arg
    assert run_python(split("--help")) == 2  # unsupported arg

    assert run_python(split("-c 'f=42'")) == 0
    assert run_python(split("-c 'f=1/0'")) == 1
    assert run_python(split("-m examples.pkg-with-main")) == 0
    assert run_python(split("examples/single-file/file-with-main.py")) == 0

    with patch("cosmofy.updater.repl.interact") as _interact:
        assert run_python(split("-i")) == 0
        assert _interact.called

        assert run_python(split("-ic f=42")) == 0
        assert _interact.called


def test_main() -> None:
    """Argument interceptor."""
    assert main(split("-V")) == 0  # runs python --version

    with patch("cosmofy.updater.self_update") as _self_update:
        _self_update.return_value = 0
        assert main(split("-m other-module --option --self-update")) == 0
