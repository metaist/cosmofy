"""Test fs ls command."""

# std
from datetime import datetime
from pathlib import Path
from shlex import split
from zipfile import ZipInfo
import json
import tempfile

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.fs.ls import Args
from cosmofy.fs.ls import human_size
from cosmofy.fs.ls import ls_time
from cosmofy.fs.ls import Runner
from cosmofy.zipfile2 import ZipFile2


def test_human_size_bytes() -> None:
    """Test human_size for byte-sized values."""
    assert human_size(0) == "0B"
    assert human_size(512) == "512B"
    assert human_size(1023) == "1023B"


def test_human_size_kb() -> None:
    """Test human_size for kilobyte values."""
    assert human_size(1024) == "1K"
    assert human_size(1536) == "1.5K"
    assert human_size(2048) == "2K"


def test_human_size_mb() -> None:
    """Test human_size for megabyte values."""
    assert human_size(1024 * 1024) == "1M"
    assert human_size(1024 * 1024 * 1.5) == "1.5M"


def test_human_size_si() -> None:
    """Test human_size with SI units (1000-based)."""
    assert human_size(1000, si=True) == "1k"
    assert human_size(1500, si=True) == "1.5k"
    assert human_size(1000 * 1000, si=True) == "1m"


def test_human_size_large() -> None:
    """Test human_size for very large values."""
    assert human_size(1024**4) == "1T"
    assert human_size(1024**8) == "1Y"
    # Test cap at Y
    assert human_size(1024**9) == "1024Y"


def test_ls_time_recent() -> None:
    """Test ls_time for dates within 6 months."""
    now = datetime(2024, 6, 15, 14, 30)
    dt = datetime(2024, 5, 10, 9, 45)
    result = ls_time(dt, now=now)
    assert "May" in result
    assert "10" in result
    assert "09:45" in result


def test_ls_time_old() -> None:
    """Test ls_time for dates older than 6 months."""
    now = datetime(2024, 6, 15, 14, 30)
    dt = datetime(2023, 5, 10, 9, 45)
    result = ls_time(dt, now=now)
    assert "May" in result
    assert "10" in result
    assert "2023" in result
    assert ":" not in result  # no time, just year


def test_ls_time_future() -> None:
    """Test ls_time for future dates."""
    now = datetime(2024, 6, 15, 14, 30)
    dt = datetime(2025, 1, 1, 0, 0)
    result = ls_time(dt, now=now)
    assert "2025" in result


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip"))
    assert args.bundle == Path("bundle.zip")
    assert args.all is False
    assert args.long is False
    assert args.sort == "name"

    args = baton.parse(Args, split("bundle.zip -alhr --sort time"))
    assert args.all is True
    assert args.long is True
    assert args.human_readable is True
    assert args.reverse is True
    assert args.sort == "time"


def test_arg_parsing_filters() -> None:
    """Test filter argument parsing."""
    args = baton.parse(Args, split("bundle.zip --hide *.pyc --ignore __pycache__"))
    assert "*.pyc" in args.hide
    assert "__pycache__" in args.ignore


def test_runner_should_include() -> None:
    """Test Runner.should_include filtering logic."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with ZipFile2(f.name, "w") as z:
            z.writestr("file.txt", "test")

        with ZipFile2(f.name, "r") as bundle:
            # Default: hide dotfiles
            args = baton.parse(Args, split("bundle.zip"))
            runner = Runner(bundle, args)
            assert runner.should_include("file.txt") is True
            assert runner.should_include(".hidden") is False

            # With --all: show dotfiles
            args = baton.parse(Args, split("bundle.zip --all"))
            runner = Runner(bundle, args)
            assert runner.should_include(".hidden") is True

            # With --hide: hide matching unless --all
            args = baton.parse(Args, split("bundle.zip --hide *.pyc"))
            runner = Runner(bundle, args)
            assert runner.should_include("test.pyc") is False
            assert runner.should_include("test.py") is True

            # With --ignore: always hide even with --all
            args = baton.parse(Args, split("bundle.zip --all --ignore *.pyc"))
            runner = Runner(bundle, args)
            assert runner.should_include("test.pyc") is False


def test_runner_get_extension() -> None:
    """Test Runner.get_extension for sorting."""
    # File with extension
    info = ZipInfo("path/to/file.txt")
    result = Runner.get_extension(info)
    assert result == ("path/to", "txt", "file")

    # File without extension
    info = ZipInfo("path/to/README")
    result = Runner.get_extension(info)
    assert result == ("path/to", "", "README")

    # Directory
    info = ZipInfo("path/to/dir/")
    result = Runner.get_extension(info)
    assert result == ("path/to", "", "dir")


def test_runner_sort() -> None:
    """Test Runner.sort with different modes."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with ZipFile2(f.name, "w") as z:
            z.writestr("a.txt", "test")
            z.writestr("b.txt", "longer content")
            z.writestr("c.txt", "x")

        with ZipFile2(f.name, "r") as bundle:
            files = list(bundle.infolist())

            # Sort by name
            args = baton.parse(Args, split("bundle.zip --sort name"))
            runner = Runner(bundle, args)
            result = list(runner.sort(files))
            assert result[0].filename == "a.txt"

            # Sort by name reversed
            args = baton.parse(Args, split("bundle.zip --sort name --reverse"))
            runner = Runner(bundle, args)
            result = list(runner.sort(files))
            assert result[0].filename == "c.txt"

            # Sort by size (biggest first by default)
            args = baton.parse(Args, split("bundle.zip --sort size"))
            runner = Runner(bundle, args)
            result = list(runner.sort(files))
            assert result[0].filename == "b.txt"

            # Sort none
            args = baton.parse(Args, split("bundle.zip --sort none"))
            runner = Runner(bundle, args)
            result = list(runner.sort(files))
            # Should preserve original order
            assert len(result) == 3


def test_runner_format() -> None:
    """Test Runner.format output formatting."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with ZipFile2(f.name, "w") as z:
            z.writestr("test.txt", "hello")

        with ZipFile2(f.name, "r") as bundle:
            info = bundle.getinfo("test.txt")

            # Short format
            args = baton.parse(Args, split("bundle.zip"))
            runner = Runner(bundle, args)
            result = runner.format(info)
            assert result == "test.txt"

            # Long format
            args = baton.parse(Args, split("bundle.zip -l"))
            runner = Runner(bundle, args)
            result = runner.format(info)
            assert "test.txt" in result
            assert "5" in result  # size is 5 bytes

            # Human readable
            args = baton.parse(Args, split("bundle.zip -lh"))
            runner = Runner(bundle, args)
            result = runner.format(info)
            assert "5B" in result


def test_runner_sort_time() -> None:
    """Test Runner.sort by time."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with ZipFile2(f.name, "w") as z:
            info1 = ZipInfo("old.txt", date_time=(2020, 1, 1, 0, 0, 0))
            z.writestr(info1, "old")
            info2 = ZipInfo("new.txt", date_time=(2024, 1, 1, 0, 0, 0))
            z.writestr(info2, "new")

        with ZipFile2(f.name, "r") as bundle:
            files = list(bundle.infolist())

            # Sort by time (newest first by default)
            args = baton.parse(Args, split("bundle.zip --sort time"))
            runner = Runner(bundle, args)
            result = list(runner.sort(files))
            assert result[0].filename == "new.txt"


def test_runner_sort_extension() -> None:
    """Test Runner.sort by extension."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with ZipFile2(f.name, "w") as z:
            z.writestr("file.py", "python")
            z.writestr("file.txt", "text")
            z.writestr("file.md", "markdown")

        with ZipFile2(f.name, "r") as bundle:
            files = list(bundle.infolist())

            # Sort by extension
            args = baton.parse(Args, split("bundle.zip --sort extension"))
            runner = Runner(bundle, args)
            result = list(runner.sort(files))
            # Sorted by extension: md, py, txt
            extensions = [r.filename.split(".")[-1] for r in result]
            assert extensions == sorted(extensions)


def test_runner_get_files() -> None:
    """Test Runner.get_files iterates correctly."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("dir/", "")
            z.writestr("dir/file1.txt", "content1")
            z.writestr("dir/file2.txt", "content2")
            z.writestr(".hidden", "hidden")
            z.writestr("visible.txt", "visible")

        with ZipFile2(path, "r") as bundle:
            # List directory contents
            args = baton.parse(Args, split(f"{path} dir/"))
            runner = Runner(bundle, args)
            files = list(runner.get_files())
            names = [f.filename for f in files]
            assert "dir/" in names
            assert "dir/file1.txt" in names
            assert "dir/file2.txt" in names

            # List root with --all shows hidden
            args = baton.parse(Args, split(f"{path} --all .hidden"))
            runner = Runner(bundle, args)
            files = list(runner.get_files())
            names = [f.filename for f in files]
            assert ".hidden" in names
    finally:
        path.unlink(missing_ok=True)


def test_runner_get_files_deduplicates() -> None:
    """Test Runner.get_files deduplicates when same file matched multiple times."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("file.txt", "content")

        with ZipFile2(path, "r") as bundle:
            # Request the same file twice via different patterns
            args = baton.parse(Args, split(f"{path} file.txt file.txt"))
            runner = Runner(bundle, args)
            files = list(runner.get_files())
            # Should only appear once
            assert len(files) == 1
            assert files[0].filename == "file.txt"
    finally:
        path.unlink(missing_ok=True)


def test_runner_get_files_excludes_hidden() -> None:
    """Test Runner.get_files excludes hidden files by default."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("dir/", "")
            z.writestr("dir/.hidden", "hidden")
            z.writestr("dir/visible.txt", "visible")

        with ZipFile2(path, "r") as bundle:
            # List dir without --all, hidden file should be excluded
            args = baton.parse(Args, split(f"{path} dir/"))
            runner = Runner(bundle, args)
            files = list(runner.get_files())
            names = [f.filename for f in files]
            assert "dir/visible.txt" in names
            assert "dir/.hidden" not in names
    finally:
        path.unlink(missing_ok=True)


def test_runner_get_files_not_found() -> None:
    """Test Runner.get_files raises on nonexistent file."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("exists.txt", "content")

        with ZipFile2(path, "r") as bundle:
            args = baton.parse(Args, split(f"{path} nonexistent.txt"))
            runner = Runner(bundle, args)
            with pytest.raises(FileNotFoundError):
                list(runner.get_files())
    finally:
        path.unlink(missing_ok=True)


def test_runner_run(capsys: pytest.CaptureFixture[str]) -> None:
    """Test Runner.run prints files."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("file.txt", "content")

        with ZipFile2(path, "r") as bundle:
            args = baton.parse(Args, split(f"{path} file.txt"))
            runner = Runner(bundle, args)
            runner.run()

            captured = capsys.readouterr()
            assert "file.txt" in captured.out
    finally:
        path.unlink(missing_ok=True)


def test_run_success(tmp_path: Path) -> None:
    """Test run command success."""
    from cosmofy.fs.ls import run

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("file.txt", "content")

    args = baton.parse(Args, split(f"{bundle_path}"))
    result = run(args)
    assert result == 0


def test_run_with_file_pattern(tmp_path: Path) -> None:
    """Test run command with specific file pattern."""
    from cosmofy.fs.ls import run

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("file.txt", "content")
        z.writestr("other.txt", "other")

    args = baton.parse(Args, split(f"{bundle_path} file.txt"))
    result = run(args)
    assert result == 0


def test_run_dry_run(tmp_path: Path) -> None:
    """Test run command with dry_run."""
    from cosmofy.fs.ls import run

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("file.txt", "content")

    args = baton.parse(Args, split(f"{bundle_path} --dry-run"))
    result = run(args)
    assert result == 0


def test_run_ignore_backups(tmp_path: Path) -> None:
    """Test run command with --ignore-backups."""
    from cosmofy.fs.ls import run

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("file.txt", "content")
        z.writestr("file.txt~", "backup")

    args = baton.parse(Args, split(f"{bundle_path} -B"))
    result = run(args)
    assert result == 0


def test_run_error(tmp_path: Path) -> None:
    """Test run command returns error on failure."""
    from cosmofy.fs.ls import run

    args = baton.parse(Args, split("nonexistent.zip"))
    result = run(args)
    assert result == 2


def test_runner_get_zipinfo_synthetic() -> None:
    """Test Runner.get_zipinfo returns synthetic record for missing entries."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            # Create file without explicit dir entry
            z.writestr("dir/file.txt", "content")

        with ZipFile2(path, "r") as bundle:
            from zipfile import Path as ZipPath

            args = baton.parse(Args, split(f"{path}"))
            runner = Runner(bundle, args)

            # dir/ doesn't have an entry but exists implicitly
            zip_path = ZipPath(bundle) / "dir/"
            info = runner.get_zipinfo(zip_path)
            # It creates a synthetic ZipInfo with the path
            assert "dir" in info.filename
    finally:
        path.unlink(missing_ok=True)


def test_runner_to_dict() -> None:
    """Test Runner.to_dict converts ZipInfo to dictionary."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("file.txt", "content")

        with ZipFile2(path, "r") as bundle:
            args = baton.parse(Args, split(f"{path}"))
            runner = Runner(bundle, args)
            info = bundle.getinfo("file.txt")
            result = runner.to_dict(info)

            assert result["filename"] == "file.txt"
            assert result["file_size"] == 7
            assert result["is_dir"] is False
            assert "date_time" in result
    finally:
        path.unlink(missing_ok=True)


def test_runner_run_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Test Runner.run with JSON output."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        with ZipFile2(path, "w") as z:
            z.writestr("file.txt", "content")

        with ZipFile2(path, "r") as bundle:
            args = baton.parse(Args, split(f"{path} file.txt --output-format json"))
            runner = Runner(bundle, args)
            runner.run()

            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["filename"] == "file.txt"
    finally:
        path.unlink(missing_ok=True)
