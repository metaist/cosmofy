"""Test bundle."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch
import tempfile
import zipfile

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.bundle import Args
from cosmofy.bundle import Bundler
from cosmofy.bundle import ensure_uv
from cosmofy.bundle import find_project_root
from cosmofy.bundle import open_zip
from cosmofy.bundle import venv_site_packages
from cosmofy.fs.add import Args as FsAddArgs


def test_suffix_arg_parsing() -> None:
    """Test --suffix argument parsing."""
    have = baton.parse(Args, split(""))
    assert have.suffix is None, "default is None"

    have = baton.parse(Args, split("--suffix .exe"))
    assert have.suffix == ".exe", "explicit suffix"

    have = baton.parse(Args, split("-s .com"))
    assert have.suffix == ".com", "short flag"

    have = baton.parse(Args, split("--suffix="))
    assert have.suffix == "", "explicit empty suffix"


@patch("cosmofy.bundle.platform.system")
def test_suffix_default_windows(mock_system: MagicMock) -> None:
    """Test default suffix on Windows."""
    mock_system.return_value = "Windows"
    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    assert bundler.suffix == ".com", "default .com on Windows"


@patch("cosmofy.bundle.platform.system")
def test_suffix_default_linux(mock_system: MagicMock) -> None:
    """Test default suffix on Linux."""
    mock_system.return_value = "Linux"
    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    assert bundler.suffix == "", "default empty on Linux"


@patch("cosmofy.bundle.platform.system")
def test_suffix_default_darwin(mock_system: MagicMock) -> None:
    """Test default suffix on macOS."""
    mock_system.return_value = "Darwin"
    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    assert bundler.suffix == "", "default empty on macOS"


@patch("cosmofy.bundle.platform.system")
def test_suffix_explicit_override(mock_system: MagicMock) -> None:
    """Test explicit suffix overrides platform default."""
    mock_system.return_value = "Windows"
    args = baton.parse(Args, split("--suffix .exe"))
    bundler = Bundler(args)
    assert bundler.suffix == ".exe", "explicit suffix overrides default"


@patch("cosmofy.bundle.platform.system")
def test_suffix_explicit_empty_on_windows(mock_system: MagicMock) -> None:
    """Test explicit empty suffix on Windows."""
    mock_system.return_value = "Windows"
    args = baton.parse(Args, split("--suffix="))
    bundler = Bundler(args)
    assert bundler.suffix == "", "explicit empty suffix on Windows"


def test_compile_bytecode_arg_parsing() -> None:
    """Test --compile-bytecode argument parsing for bundle."""
    have = baton.parse(Args, split(""))
    assert have.compile_bytecode is False, "default is False"

    have = baton.parse(Args, split("--compile-bytecode"))
    assert have.compile_bytecode is True, "long flag"

    have = baton.parse(Args, split("-c"))
    assert have.compile_bytecode is True, "short flag"


def test_fs_add_compile_bytecode_arg_parsing() -> None:
    """Test --compile-bytecode argument parsing for fs add."""
    have = baton.parse(FsAddArgs, split("bundle.zip file.py"))
    assert have.compile_bytecode is False, "default is False"

    have = baton.parse(FsAddArgs, split("bundle.zip --compile-bytecode file.py"))
    assert have.compile_bytecode is True, "long flag"

    have = baton.parse(FsAddArgs, split("bundle.zip -c file.py"))
    assert have.compile_bytecode is True, "short flag"


def test_open_zip() -> None:
    """Test open_zip wrapper."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        path = Path(f.name)

    try:
        # Create a new zip
        with open_zip(path, mode="w") as z:
            z.writestr("test.txt", "hello")

        # Verify it was created with compression
        with zipfile.ZipFile(path) as z:
            info = z.getinfo("test.txt")
            assert info.compress_type == zipfile.ZIP_DEFLATED
            assert z.read("test.txt") == b"hello"
    finally:
        path.unlink(missing_ok=True)


def test_ensure_uv_found() -> None:
    """Test ensure_uv when uv is installed."""
    with patch("cosmofy.bundle.shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/uv"
        assert ensure_uv() is True
        mock_which.assert_called_once_with("uv")


def test_ensure_uv_not_found() -> None:
    """Test ensure_uv when uv is not installed."""
    with patch("cosmofy.bundle.shutil.which") as mock_which:
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError) as exc:
            ensure_uv()
        assert "cannot find command: `uv`" in str(exc.value)
        assert "tip:" in str(exc.value)


def test_find_project_root(tmp_path: Path) -> None:
    """Test find_project_root finds pyproject.toml."""
    # Create nested structure
    subdir = tmp_path / "a" / "b" / "c"
    subdir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").touch()

    # Should find root from nested dir
    result = find_project_root(subdir)
    assert result == tmp_path


def test_find_project_root_not_found(tmp_path: Path) -> None:
    """Test find_project_root raises when no pyproject.toml."""
    with pytest.raises(FileNotFoundError) as exc:
        find_project_root(tmp_path)
    assert "no `pyproject.toml` found" in str(exc.value)


def test_venv_site_packages_posix(tmp_path: Path) -> None:
    """Test venv_site_packages on posix-like structure."""
    # Create posix venv structure
    sp = tmp_path / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)

    result = venv_site_packages(tmp_path)
    assert result == sp


def test_venv_site_packages_windows(tmp_path: Path) -> None:
    """Test venv_site_packages on Windows-like structure."""
    # Create Windows venv structure
    sp = tmp_path / "Lib" / "site-packages"
    sp.mkdir(parents=True)

    result = venv_site_packages(tmp_path)
    assert result == sp


def test_venv_site_packages_not_found(tmp_path: Path) -> None:
    """Test venv_site_packages raises when no site-packages."""
    with pytest.raises(FileNotFoundError) as exc:
        venv_site_packages(tmp_path)
    assert "cannot find `site-packages`" in str(exc.value)


def test_venv_site_packages_multiple_versions(tmp_path: Path) -> None:
    """Test venv_site_packages picks latest version."""
    # Create multiple python versions
    for ver in ["python3.10", "python3.11", "python3.12"]:
        sp = tmp_path / "lib" / ver / "site-packages"
        sp.mkdir(parents=True)

    result = venv_site_packages(tmp_path)
    assert "python3.12" in str(result)


def test_console_scripts_from_venv(tmp_path: Path) -> None:
    """Test console_scripts_from_venv retrieves entry points."""
    from cosmofy.bundle import console_scripts_from_venv

    # Create venv structure
    sp = tmp_path / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)

    # Create dist-info with entry points
    dist_info = sp / "mypackage-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Name: mypackage\nVersion: 1.0\n")
    (dist_info / "entry_points.txt").write_text(
        "[console_scripts]\nmycmd = mypackage.cli:main\n"
    )

    result = console_scripts_from_venv("mypackage", tmp_path)
    assert "mycmd" in result
    assert result["mycmd"] == "mypackage.cli:main"


def test_console_scripts_from_venv_normalized(tmp_path: Path) -> None:
    """Test console_scripts_from_venv normalizes package names (PEP 503)."""
    from cosmofy.bundle import console_scripts_from_venv

    sp = tmp_path / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)

    # dist-info with underscores/dots
    dist_info = sp / "my_cool.package-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Name: my_cool.package\nVersion: 1.0\n")
    (dist_info / "entry_points.txt").write_text(
        "[console_scripts]\ncool = my_cool.package:main\n"
    )

    # Query with different forms - should all match
    result = console_scripts_from_venv("my-cool-package", tmp_path)
    assert "cool" in result


def test_console_scripts_from_venv_not_found(tmp_path: Path) -> None:
    """Test console_scripts_from_venv returns empty when package not found."""
    from cosmofy.bundle import console_scripts_from_venv

    sp = tmp_path / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)

    result = console_scripts_from_venv("nonexistent", tmp_path)
    assert result == {}


def test_bundler_fs_copy(tmp_path: Path) -> None:
    """Test Bundler.fs_copy copies file."""
    src = tmp_path / "src.txt"
    src.write_text("content")
    dest = tmp_path / "dest.txt"

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    result = bundler.fs_copy(src, dest)

    assert result == dest
    assert dest.exists()
    assert dest.read_text() == "content"


def test_bundler_fs_copy_dry_run(tmp_path: Path) -> None:
    """Test Bundler.fs_copy in dry-run mode."""
    src = tmp_path / "src.txt"
    src.write_text("content")
    dest = tmp_path / "dest.txt"

    args = baton.parse(Args, split("--dry-run"))
    bundler = Bundler(args)
    result = bundler.fs_copy(src, dest)

    assert result == dest
    assert not dest.exists()  # Not actually copied


def test_bundler_fs_set_executable(tmp_path: Path) -> None:
    """Test Bundler.fs_set_executable sets executable bit."""
    import stat

    src = tmp_path / "script.sh"
    src.write_text("#!/bin/bash")
    src.chmod(0o644)

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    result = bundler.fs_set_executable(src)

    assert result == src
    mode = src.stat().st_mode
    assert mode & stat.S_IXUSR  # User execute


def test_bundler_fs_set_executable_dry_run(tmp_path: Path) -> None:
    """Test Bundler.fs_set_executable in dry-run mode."""

    src = tmp_path / "script.sh"
    src.write_text("#!/bin/bash")
    src.chmod(0o644)
    original_mode = src.stat().st_mode

    args = baton.parse(Args, split("--dry-run"))
    bundler = Bundler(args)
    result = bundler.fs_set_executable(src)

    assert result == src
    assert src.stat().st_mode == original_mode  # Not changed


@patch("cosmofy.bundle.download_if_newer")
def test_bundler_from_cache(mock_download: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.from_cache downloads and copies."""
    src = tmp_path / "cache" / "python"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"python binary")
    dest = tmp_path / "python"

    args = baton.parse(Args, split(""))
    args.python_url = "https://example.com/python"
    bundler = Bundler(args)
    result = bundler.from_cache(src, dest)

    assert result == dest
    mock_download.assert_called_once_with("https://example.com/python", src)


@patch("cosmofy.bundle.download_if_newer")
def test_bundler_from_cache_dry_run(mock_download: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.from_cache in dry-run mode."""
    src = tmp_path / "cache" / "python"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"python binary")
    dest = tmp_path / "python"

    args = baton.parse(Args, split("--dry-run"))
    args.python_url = "https://example.com/python"
    bundler = Bundler(args)
    result = bundler.from_cache(src, dest)

    assert result == dest
    mock_download.assert_not_called()


@patch("cosmofy.bundle.download")
def test_bundler_from_download(mock_download: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.from_download downloads fresh."""
    dest = tmp_path / "python"
    dest.write_bytes(b"python binary")

    args = baton.parse(Args, split(""))
    args.python_url = "https://example.com/python"
    bundler = Bundler(args)
    result = bundler.from_download(dest)

    assert result == dest
    mock_download.assert_called_once_with("https://example.com/python", dest)


@patch("cosmofy.bundle.download")
def test_bundler_from_download_dry_run(
    mock_download: MagicMock, tmp_path: Path
) -> None:
    """Test Bundler.from_download in dry-run mode."""
    dest = tmp_path / "python"
    dest.write_bytes(b"python binary")

    args = baton.parse(Args, split("--dry-run"))
    args.python_url = "https://example.com/python"
    bundler = Bundler(args)
    result = bundler.from_download(dest)

    assert result == dest
    mock_download.assert_not_called()


@patch("cosmofy.bundle.download")
def test_bundler_get_cosmo_python_no_cache(
    mock_download: MagicMock, tmp_path: Path
) -> None:
    """Test Bundler.get_cosmo_python with no_cache."""
    dest = tmp_path / "python"
    dest.write_bytes(b"python binary")

    args = baton.parse(Args, split("--no-cache"))
    args.python_url = "https://example.com/python"
    bundler = Bundler(args)
    result = bundler.get_cosmo_python(dest)

    assert result == dest
    mock_download.assert_called_once()


@patch("cosmofy.bundle.download_if_newer")
def test_bundler_get_cosmo_python_with_cache(
    mock_download: MagicMock, tmp_path: Path
) -> None:
    """Test Bundler.get_cosmo_python with cache."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached_python = cache_dir / "python"
    cached_python.write_bytes(b"cached python")
    dest = tmp_path / "python"

    args = baton.parse(Args, split(""))
    args.cache_dir = cache_dir
    args.python_url = "https://example.com/python"
    bundler = Bundler(args)
    result = bundler.get_cosmo_python(dest)

    assert result == dest
    mock_download.assert_called_once()


@patch("cosmofy.bundle.subprocess.check_output")
def test_bundler_uv_version(mock_check_output: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.uv_version returns package name and version."""
    mock_check_output.return_value = '{"package_name": "mypackage", "version": "1.2.3"}'

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    name, version = bundler.uv_version()

    assert name == "mypackage"
    assert version == "1.2.3"
    mock_check_output.assert_called_once()


@patch("cosmofy.bundle.subprocess.check_output")
def test_bundler_uv_version_dry_run(
    mock_check_output: MagicMock, tmp_path: Path
) -> None:
    """Test Bundler.uv_version in dry-run mode."""
    args = baton.parse(Args, split("--dry-run"))
    bundler = Bundler(args)
    name, version = bundler.uv_version()

    assert name == ""
    assert version == ""
    mock_check_output.assert_not_called()


@patch("cosmofy.bundle.subprocess.check_output")
def test_bundler_uv_sync(mock_check_output: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.uv_sync returns venv path."""
    venv_path = tmp_path / "venv"
    mock_check_output.return_value = (
        f'{{"sync": {{"environment": {{"path": "{venv_path}"}}}}}}'
    )

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    result = bundler.uv_sync(pkg="mypackage", version="3.11", venv=venv_path)

    assert result == venv_path
    mock_check_output.assert_called_once()


@patch("cosmofy.bundle.subprocess.check_output")
def test_bundler_uv_sync_dry_run(mock_check_output: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.uv_sync in dry-run mode."""
    args = baton.parse(Args, split("--dry-run"))
    bundler = Bundler(args)
    result = bundler.uv_sync(pkg="mypackage", version="3.11", venv=None)

    assert result == Path()
    mock_check_output.assert_not_called()


@patch("cosmofy.bundle.subprocess.check_output")
def test_bundler_uv_sync_verbose(mock_check_output: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.uv_sync with verbosity flags."""
    venv_path = tmp_path / "venv"
    mock_check_output.return_value = (
        f'{{"sync": {{"environment": {{"path": "{venv_path}"}}}}}}'
    )

    args = baton.parse(Args, split("-v"))
    bundler = Bundler(args)
    bundler.uv_sync(pkg="mypackage", version="3.11", venv=venv_path)

    call_args = mock_check_output.call_args[0][0]
    assert "-v" in call_args


@patch("cosmofy.bundle.subprocess.check_output")
def test_bundler_uv_sync_quiet(mock_check_output: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.uv_sync with quiet flags."""
    venv_path = tmp_path / "venv"
    mock_check_output.return_value = (
        f'{{"sync": {{"environment": {{"path": "{venv_path}"}}}}}}'
    )

    args = baton.parse(Args, split("-q"))
    bundler = Bundler(args)
    bundler.uv_sync(pkg="mypackage", version="3.11", venv=venv_path)

    call_args = mock_check_output.call_args[0][0]
    assert "-q" in call_args


@patch("cosmofy.bundle.subprocess.check_output")
def test_bundler_uv_sync_script(mock_check_output: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.uv_sync with script."""
    venv_path = tmp_path / "venv"
    script_path = tmp_path / "script.py"
    script_path.write_text("print('hello')")
    mock_check_output.return_value = (
        f'{{"sync": {{"environment": {{"path": "{venv_path}"}}}}}}'
    )

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    bundler.uv_sync(pkg="script.py", version="3.11", venv=venv_path, script=script_path)

    call_args = mock_check_output.call_args[0][0]
    assert "--script" in call_args
    assert "--active" in call_args


@patch("cosmofy.bundle.add_path")
def test_bundler_bundle_venv(mock_add_path: MagicMock, tmp_path: Path) -> None:
    """Test Bundler.bundle_venv adds files to bundle."""
    # Create venv structure with files
    sp = tmp_path / "venv" / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)
    (sp / "mymodule.py").write_text("# module")

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        bundle_path = Path(f.name)

    try:
        with open_zip(bundle_path, mode="w") as bundle:
            bundler.bundle_venv(bundle, tmp_path / "venv")

        mock_add_path.assert_called()
    finally:
        bundle_path.unlink(missing_ok=True)


@patch("cosmofy.bundle.add_path")
def test_bundler_bundle_venv_excludes_uv_artifacts(
    mock_add_path: MagicMock, tmp_path: Path
) -> None:
    """Test Bundler.bundle_venv excludes uv artifacts."""
    sp = tmp_path / "venv" / "lib" / "python3.11" / "site-packages"
    dist_info = sp / "mypackage-1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text("Name: mypackage")
    (dist_info / "direct_url.json").write_text("{}")
    (dist_info / "uv_build.json").write_text("{}")

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        bundle_path = Path(f.name)

    try:
        with open_zip(bundle_path, mode="w") as bundle:
            bundler.bundle_venv(bundle, tmp_path / "venv")

        # Check that add_path was not called for excluded files
        for call in mock_add_path.call_args_list:
            src_path = call[0][1]  # Second positional arg is src
            assert "direct_url.json" not in str(src_path)
            assert "uv_build.json" not in str(src_path)
    finally:
        bundle_path.unlink(missing_ok=True)


@patch("cosmofy.bundle.set_args")
@patch("cosmofy.bundle.add_path")
def test_bundler_bundle_entry_point(
    mock_add_path: MagicMock, mock_set_args: MagicMock, tmp_path: Path
) -> None:
    """Test Bundler.bundle_entry_point creates bundle."""
    # Create a minimal zip file as source
    src = tmp_path / "python"
    with open_zip(src, mode="w") as z:
        z.writestr("test.txt", "hello")

    # Create venv structure
    sp = tmp_path / "venv" / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)
    (sp / "mymodule.py").write_text("# module")

    dest = tmp_path / "mycmd"

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    result = bundler.bundle_entry_point(
        src, dest, entry_point="mymodule:main", venv=tmp_path / "venv"
    )

    assert result == dest
    assert dest.exists()
    mock_set_args.assert_called_once()


@patch("cosmofy.bundle.set_args")
def test_bundler_bundle_entry_point_no_venv(
    mock_set_args: MagicMock, tmp_path: Path
) -> None:
    """Test Bundler.bundle_entry_point without venv."""
    src = tmp_path / "python"
    with open_zip(src, mode="w") as z:
        z.writestr("test.txt", "hello")

    dest = tmp_path / "mycmd"

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    result = bundler.bundle_entry_point(src, dest, entry_point="mymodule:main")

    assert result == dest
    assert dest.exists()
    mock_set_args.assert_called_once()


@patch("cosmofy.bundle.console_scripts_from_venv")
@patch("cosmofy.bundle.Bundler.bundle_entry_point")
@patch("cosmofy.bundle.Bundler.uv_sync")
def test_bundler_bundle_entry_points(
    mock_uv_sync: MagicMock,
    mock_bundle_ep: MagicMock,
    mock_console_scripts: MagicMock,
    tmp_path: Path,
) -> None:
    """Test Bundler.bundle_entry_points bundles all entries."""
    venv = tmp_path / "venv"
    mock_uv_sync.return_value = venv
    mock_console_scripts.return_value = {"cmd1": "pkg:main1", "cmd2": "pkg:main2"}
    mock_bundle_ep.return_value = tmp_path / "cmd1"

    cosmo_python = tmp_path / "python"
    cosmo_python.write_bytes(b"python")
    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    result = bundler.bundle_entry_points(
        "mypackage", "3.11", venv, cosmo_python, output_dir
    )

    assert "cmd1" in result
    assert "cmd2" in result
    assert mock_bundle_ep.call_count == 2


@patch("cosmofy.bundle.console_scripts_from_venv")
@patch("cosmofy.bundle.Bundler.uv_sync")
def test_bundler_bundle_entry_points_not_found(
    mock_uv_sync: MagicMock,
    mock_console_scripts: MagicMock,
    tmp_path: Path,
) -> None:
    """Test Bundler.bundle_entry_points raises when entry point not found."""
    venv = tmp_path / "venv"
    mock_uv_sync.return_value = venv
    mock_console_scripts.return_value = {"cmd1": "pkg:main1"}

    cosmo_python = tmp_path / "python"
    cosmo_python.write_bytes(b"python")
    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    args = baton.parse(Args, split("--entry nonexistent"))
    bundler = Bundler(args)

    with pytest.raises(ValueError) as exc:
        bundler.bundle_entry_points("mypackage", "3.11", venv, cosmo_python, output_dir)
    assert "could not find entry point" in str(exc.value)


@patch("cosmofy.bundle.set_args")
@patch("cosmofy.bundle.add_path")
@patch("cosmofy.bundle.Bundler.bundle_venv")
@patch("cosmofy.bundle.Bundler.uv_sync")
def test_bundler_bundle_script(
    mock_uv_sync: MagicMock,
    mock_bundle_venv: MagicMock,
    mock_add_path: MagicMock,
    mock_set_args: MagicMock,
    tmp_path: Path,
) -> None:
    """Test Bundler.bundle_script bundles a script."""
    venv = tmp_path / "venv"
    mock_uv_sync.return_value = venv

    # Create venv structure for bundle_venv to use
    sp = venv / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)

    script = tmp_path / "myscript.py"
    script.write_text("print('hello')")

    cosmo_python = tmp_path / "python"
    with open_zip(cosmo_python, mode="w") as z:
        z.writestr("test.txt", "hello")

    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    result = bundler.bundle_script("3.11", venv, cosmo_python, output_dir, script)

    assert result == script
    mock_set_args.assert_called_once()


def test_bundler_bundle_script_not_found(tmp_path: Path) -> None:
    """Test Bundler.bundle_script raises when script not found."""
    script = tmp_path / "nonexistent.py"
    cosmo_python = tmp_path / "python"
    cosmo_python.write_bytes(b"python")

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)

    with pytest.raises(FileNotFoundError) as exc:
        bundler.bundle_script("3.11", None, cosmo_python, None, script)
    assert "cannot find script file" in str(exc.value)


@patch("cosmofy.bundle.set_args")
@patch("cosmofy.bundle.add_path")
@patch("cosmofy.bundle.Bundler.bundle_venv")
@patch("cosmofy.bundle.Bundler.uv_sync")
def test_bundler_bundle_script_compile_bytecode(
    mock_uv_sync: MagicMock,
    mock_bundle_venv: MagicMock,
    mock_add_path: MagicMock,
    mock_set_args: MagicMock,
    tmp_path: Path,
) -> None:
    """Test Bundler.bundle_script with compile_bytecode."""
    venv = tmp_path / "venv"
    mock_uv_sync.return_value = venv

    sp = venv / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)

    script = tmp_path / "myscript.py"
    script.write_text("print('hello')")

    cosmo_python = tmp_path / "python"
    with open_zip(cosmo_python, mode="w") as z:
        z.writestr("test.txt", "hello")

    args = baton.parse(Args, split("--compile-bytecode"))
    bundler = Bundler(args)
    bundler.cosmo_python = cosmo_python
    bundler.bundle_script("3.11", venv, cosmo_python, None, script)

    # Check that set_args was called with .pyc destination
    call_args = mock_set_args.call_args
    assert ".pyc" in call_args[0][1] or "pyc" in str(call_args)


@patch("cosmofy.bundle.Bundler.bundle_entry_points")
@patch("cosmofy.bundle.Bundler.uv_version")
@patch("cosmofy.bundle.get_version")
@patch("cosmofy.bundle.Bundler.get_cosmo_python")
@patch("cosmofy.bundle.find_project_root")
def test_bundler_run(
    mock_find_root: MagicMock,
    mock_get_cosmo: MagicMock,
    mock_get_version: MagicMock,
    mock_uv_version: MagicMock,
    mock_bundle_eps: MagicMock,
    tmp_path: Path,
) -> None:
    """Test Bundler.run orchestrates bundling."""
    mock_find_root.return_value = tmp_path
    cosmo_python = tmp_path / "python"
    cosmo_python.write_bytes(b"python")
    mock_get_cosmo.return_value = cosmo_python
    mock_get_version.return_value = "3.11.0"
    mock_uv_version.return_value = ("mypackage", "1.0.0")
    mock_bundle_eps.return_value = {}

    output_dir = tmp_path / "dist"

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)
    bundler.run()

    mock_bundle_eps.assert_called_once()
    assert output_dir.exists()


@patch("cosmofy.bundle.get_version")
@patch("cosmofy.bundle.Bundler.get_cosmo_python")
def test_bundler_run_no_version(
    mock_get_cosmo: MagicMock,
    mock_get_version: MagicMock,
    tmp_path: Path,
) -> None:
    """Test Bundler.run raises when version not detected."""
    cosmo_python = tmp_path / "python"
    cosmo_python.write_bytes(b"python")
    mock_get_cosmo.return_value = cosmo_python
    mock_get_version.return_value = ""

    args = baton.parse(Args, split(""))
    bundler = Bundler(args)

    with pytest.raises(ValueError) as exc:
        bundler.run()
    assert "could not get Cosmopolitan Python version" in str(exc.value)


@patch("cosmofy.bundle.Bundler.bundle_script")
@patch("cosmofy.bundle.get_version")
@patch("cosmofy.bundle.Bundler.get_cosmo_python")
def test_bundler_run_scripts_only(
    mock_get_cosmo: MagicMock,
    mock_get_version: MagicMock,
    mock_bundle_script: MagicMock,
    tmp_path: Path,
) -> None:
    """Test Bundler.run with scripts only."""
    cosmo_python = tmp_path / "python"
    cosmo_python.write_bytes(b"python")
    mock_get_cosmo.return_value = cosmo_python
    mock_get_version.return_value = "3.11.0"

    script = tmp_path / "myscript.py"
    script.write_text("print('hello')")

    args = baton.parse(Args, split(f"--script {script}"))
    bundler = Bundler(args)
    bundler.run()

    mock_bundle_script.assert_called_once()


@patch("cosmofy.bundle.ensure_uv")
@patch("cosmofy.bundle.Bundler.run")
def test_run_success(mock_bundler_run: MagicMock, mock_ensure_uv: MagicMock) -> None:
    """Test run function success."""
    from cosmofy.bundle import run

    mock_ensure_uv.return_value = True

    args = baton.parse(Args, split(""))
    result = run(args)

    assert result == 0
    mock_bundler_run.assert_called_once()


@patch("cosmofy.bundle.ensure_uv")
def test_run_uv_not_found(mock_ensure_uv: MagicMock) -> None:
    """Test run function when uv not found."""
    from cosmofy.bundle import run

    mock_ensure_uv.side_effect = FileNotFoundError("cannot find uv")

    args = baton.parse(Args, split(""))
    result = run(args)

    assert result == 2


@patch("cosmofy.bundle.ensure_uv")
@patch("cosmofy.bundle.Bundler.run")
def test_run_error(mock_bundler_run: MagicMock, mock_ensure_uv: MagicMock) -> None:
    """Test run function with error."""
    from cosmofy.bundle import run

    mock_ensure_uv.return_value = True
    mock_bundler_run.side_effect = Exception("Something went wrong")

    args = baton.parse(Args, split(""))
    result = run(args)

    assert result == 2
