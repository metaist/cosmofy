"""Test python CLI emulation within python."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import patch

# lib
import pytest

# pkg
from cosmofy import pythonoid
from cosmofy.pythonoid import PythonArgs
from cosmofy.pythonoid import run_python


def test_main_detector() -> None:
    """Detect __main__ blocks."""
    code = b"""if __name__ == "__main__":\n\t..."""
    assert pythonoid.RE_MAIN.search(code)

    code = b"""\nif __name__ == '__main__':\n\t..."""
    assert pythonoid.RE_MAIN.search(code)

    code = b"""\nif '__main__'  ==  __name__  :\n\t..."""
    assert pythonoid.RE_MAIN.search(code)

    code = b"""\n# if __name__ == "__main__":\n\t..."""
    assert not pythonoid.RE_MAIN.search(code)


def test_compile() -> None:
    """Compile python."""
    src = Path(__file__).parent.parent / "src" / "cosmofy" / "__init__.py"
    assert isinstance(pythonoid.compile_python(src), bytearray)
    assert isinstance(pythonoid.compile_python(src, src.read_bytes()), bytearray)


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
        PythonArgs.parse(split("-b"))


def test_run() -> None:
    """Run python CLI."""
    assert run_python(split("--help")) == 0
    assert run_python(split("--version")) == 0
    assert run_python(split("-VV")) == 0
    assert run_python(split("--fake")) == 2  # invalid arg
    assert run_python(split("-b")) == 2  # unsupported arg

    assert run_python(split("-c 'f=42'")) == 0
    assert run_python(split("-c 'f=1/0'")) == 1
    assert run_python(split("-m examples.pkg-with-main")) == 0
    assert run_python(split("examples/single-file/file-with-main.py")) == 0

    with patch("cosmofy.pythonoid.repl.interact") as _interact:
        assert run_python(split("-i")) == 0
        assert _interact.called

        assert run_python(split("-ic f=42")) == 0
        assert _interact.called
