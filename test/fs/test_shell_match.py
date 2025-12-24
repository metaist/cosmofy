# pkg
from cosmofy.fs import shell_match


def test_star_not_slash() -> None:
    assert shell_match("foo.py", "*.py") is True
    assert shell_match("dir/foo.py", "*.py") is False
    assert shell_match("foo.txt", "*.py") is False
    assert shell_match("Lib/cosmofy", "Lib/*") is True
    assert shell_match("Lib/cosmofy/__init__.py", "Lib/*") is False


def test_star_star() -> None:
    assert shell_match("Lib/cosmofy/__init__.py", "Lib/**") is True
    assert shell_match("Lib/foo.py", "Lib/**/*.py") is True
    assert shell_match("Lib/cosmofy/__init__.py", "Lib/**/*.py") is True
    assert shell_match("Lib/a/b/c/deep.py", "Lib/**/*.py") is True
    assert shell_match("Other/foo.py", "Lib/**/*.py") is False


def test_star_star_at_start() -> None:
    assert shell_match("Lib/cosmofy/foo.py", "**/cosmofy/*") is True
    assert shell_match("cosmofy/foo.py", "**/cosmofy/*") is True
    assert shell_match("Lib/cosmofy/sub/bar.py", "**/cosmofy/*") is False


def test_question_mark() -> None:
    assert shell_match("foo.py", "???.py") is True
    assert shell_match("fo.py", "???.py") is False
    assert shell_match("abcd.py", "???.py") is False


def test_dotfiles() -> None:
    assert shell_match(".hidden", "*") is False
    assert shell_match(".hidden", ".*") is True
    assert shell_match(".hidden", "?hidden") is False
    assert shell_match("dir/.hidden", "dir/*") is False
    assert shell_match("dir/.hidden", "dir/.*") is True


def test_literal() -> None:
    assert shell_match("foo.py", "foo.py") is True
    assert shell_match("foo.py", "bar.py") is False
