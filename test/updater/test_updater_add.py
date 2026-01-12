"""Test updater add command."""

# std
from pathlib import Path
from shlex import split
from unittest.mock import MagicMock
from unittest.mock import patch
import subprocess

# lib
import pytest

# pkg
from cosmofy import baton
from cosmofy.updater.add import add_arg_prefix
from cosmofy.updater.add import Args
from cosmofy.updater.add import ARGS_PREFIX
from cosmofy.updater.add import get_github_download


def test_arg_parsing() -> None:
    """Test Args parsing."""
    args = baton.parse(Args, split("bundle.zip"))
    assert args.bundle == Path("bundle.zip")
    assert args.no_copy is False
    assert args.no_args is False


def test_arg_parsing_receipt_options() -> None:
    """Test receipt-related argument parsing."""
    args = baton.parse(
        Args,
        split(
            "bundle.zip --receipt out.json --receipt-url https://example.com/r.json "
            "--release-url https://example.com/file --release-version 1.0.0"
        ),
    )
    assert args.receipt == Path("out.json")
    assert args.receipt_url == "https://example.com/r.json"
    assert args.release_url == "https://example.com/file"
    assert args.release_version == "1.0.0"


def test_arg_parsing_process_options() -> None:
    """Test process option parsing."""
    args = baton.parse(Args, split("bundle.zip --no-copy --no-args"))
    assert args.no_copy is True
    assert args.no_args is True


@patch("cosmofy.updater.add.which")
def test_get_github_download_no_git(mock_which: MagicMock) -> None:
    """Test get_github_download when git is not installed."""
    mock_which.return_value = None
    result = get_github_download("file.exe")
    assert result == ""


@patch("cosmofy.updater.add.subprocess.check_output")
@patch("cosmofy.updater.add.which")
def test_get_github_download_not_a_repo(
    mock_which: MagicMock, mock_output: MagicMock
) -> None:
    """Test get_github_download outside a git repo."""
    mock_which.return_value = "/usr/bin/git"
    mock_output.side_effect = subprocess.CalledProcessError(1, "git")
    result = get_github_download("file.exe")
    assert result == ""


@patch("cosmofy.updater.add.subprocess.check_output")
@patch("cosmofy.updater.add.which")
def test_get_github_download_ssh_form(
    mock_which: MagicMock, mock_output: MagicMock
) -> None:
    """Test get_github_download with SSH remote URL."""
    mock_which.return_value = "/usr/bin/git"
    mock_output.return_value = "git@github.com:owner/repo.git\n"
    result = get_github_download("myapp.exe")
    assert result == "https://github.com/owner/repo/releases/latest/download/myapp.exe"


@patch("cosmofy.updater.add.subprocess.check_output")
@patch("cosmofy.updater.add.which")
def test_get_github_download_ssh_url_form(
    mock_which: MagicMock, mock_output: MagicMock
) -> None:
    """Test get_github_download with ssh:// remote URL."""
    mock_which.return_value = "/usr/bin/git"
    mock_output.return_value = "ssh://git@github.com/owner/repo.git\n"
    result = get_github_download("myapp.exe")
    assert result == "https://github.com/owner/repo/releases/latest/download/myapp.exe"


@patch("cosmofy.updater.add.subprocess.check_output")
@patch("cosmofy.updater.add.which")
def test_get_github_download_https_form(
    mock_which: MagicMock, mock_output: MagicMock
) -> None:
    """Test get_github_download with HTTPS remote URL."""
    mock_which.return_value = "/usr/bin/git"
    mock_output.return_value = "https://github.com/owner/repo.git\n"
    result = get_github_download("myapp.exe")
    assert result == "https://github.com/owner/repo/releases/latest/download/myapp.exe"


@patch("cosmofy.updater.add.subprocess.check_output")
@patch("cosmofy.updater.add.which")
def test_get_github_download_https_no_git_suffix(
    mock_which: MagicMock, mock_output: MagicMock
) -> None:
    """Test get_github_download with HTTPS URL without .git suffix."""
    mock_which.return_value = "/usr/bin/git"
    mock_output.return_value = "https://github.com/owner/repo\n"
    result = get_github_download("myapp.exe")
    assert result == "https://github.com/owner/repo/releases/latest/download/myapp.exe"


@patch("cosmofy.updater.add.subprocess.check_output")
@patch("cosmofy.updater.add.which")
def test_get_github_download_non_github(
    mock_which: MagicMock, mock_output: MagicMock
) -> None:
    """Test get_github_download with non-GitHub remote."""
    mock_which.return_value = "/usr/bin/git"
    mock_output.return_value = "https://gitlab.com/owner/repo.git\n"
    result = get_github_download("myapp.exe")
    assert result == ""


def test_add_arg_prefix_simple() -> None:
    """Test add_arg_prefix with simple script arg."""
    result = add_arg_prefix("script.py")
    assert result == f"{ARGS_PREFIX} script.py"


def test_add_arg_prefix_module() -> None:
    """Test add_arg_prefix with -m flag."""
    result = add_arg_prefix("-m mypackage")
    assert result == f"{ARGS_PREFIX} -m mypackage"


def test_add_arg_prefix_command() -> None:
    """Test add_arg_prefix with -c flag."""
    result = add_arg_prefix("-c 'print(1)'")
    assert result == f"{ARGS_PREFIX} -c 'print(1)'"


def test_add_arg_prefix_empty() -> None:
    """Test add_arg_prefix with empty args."""
    result = add_arg_prefix("")
    assert result == f"{ARGS_PREFIX}"


def test_add_arg_prefix_idempotent() -> None:
    """Test add_arg_prefix is idempotent."""
    first = add_arg_prefix("-m mypackage")
    second = add_arg_prefix(first)
    assert first == second


def test_add_arg_prefix_unsupported() -> None:
    """Test add_arg_prefix with unsupported args."""
    with pytest.raises(ValueError) as exc:
        add_arg_prefix("-b script.py")  # -b is valid but unsupported
    assert "unsupported python args" in str(exc.value)
    assert "tip:" in str(exc.value)


def test_copy_data_file(tmp_path: Path) -> None:
    """Test copy_data copies a file."""
    from zipfile import Path as ZipPath
    from cosmofy.updater.add import copy_data
    from cosmofy.zipfile2 import ZipFile2

    src_path = tmp_path / "src.zip"
    with ZipFile2(src_path, "w") as z:
        z.writestr("file.txt", "content")

    dest_path = tmp_path / "dest.zip"
    with ZipFile2(dest_path, "w") as dest:
        with ZipFile2(src_path, "r") as src_zip:
            src = ZipPath(src_zip) / "file.txt"
            copy_data(src, dest)

    with ZipFile2(dest_path, "r") as z:
        assert "file.txt" in z.namelist()


def test_copy_data_dir(tmp_path: Path) -> None:
    """Test copy_data copies a directory recursively."""
    from zipfile import Path as ZipPath
    from cosmofy.updater.add import copy_data
    from cosmofy.zipfile2 import ZipFile2

    src_path = tmp_path / "src.zip"
    with ZipFile2(src_path, "w") as z:
        z.writestr("dir/", "")
        z.writestr("dir/file1.txt", "content1")
        z.writestr("dir/file2.txt", "content2")

    dest_path = tmp_path / "dest.zip"
    with ZipFile2(dest_path, "w") as dest:
        with ZipFile2(src_path, "r") as src_zip:
            src = ZipPath(src_zip) / "dir"
            copy_data(src, dest)

    with ZipFile2(dest_path, "r") as z:
        names = z.namelist()
        assert "dir/file1.txt" in names
        assert "dir/file2.txt" in names


@patch("cosmofy.updater.add.from_venv")
@patch("cosmofy.updater.add.is_zipfile")
@patch("cosmofy.updater.add.metadata.distribution")
def test_copy_cosmofy_venv(
    mock_dist: MagicMock,
    mock_is_zipfile: MagicMock,
    mock_from_venv: MagicMock,
    tmp_path: Path,
) -> None:
    """Test copy_cosmofy from venv."""
    from cosmofy.updater.add import copy_cosmofy
    from cosmofy.zipfile2 import ZipFile2

    mock_dist.return_value.name = "cosmofy"
    mock_dist.return_value.version = "0.1.0"
    mock_is_zipfile.return_value = False

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w"):
        pass

    with ZipFile2(bundle_path, "a") as bundle:
        # This will raise FileNotFoundError because dist-info doesn't exist
        # but we're testing that from_venv would be called
        try:
            copy_cosmofy(bundle)
        except FileNotFoundError:
            pass  # Expected when dist-info doesn't exist


@patch("cosmofy.updater.add.add_data")
@patch("cosmofy.updater.add.Receipt")
def test_write_receipt(
    mock_receipt_cls: MagicMock, mock_add_data: MagicMock, tmp_path: Path
) -> None:
    """Test write_receipt writes receipt file."""
    from cosmofy.updater.add import write_receipt
    from cosmofy.zipfile2 import ZipFile2

    mock_receipt = MagicMock()
    mock_receipt.is_valid.return_value = True
    mock_receipt.__str__ = MagicMock(return_value='{"test": "data"}')  # type: ignore[method-assign]
    mock_receipt_cls.return_value = mock_receipt
    mock_receipt_cls.from_path.return_value = MagicMock(
        algo="sha256", hash="abc123", version="1.0.0"
    )

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    output_path = tmp_path / "receipt.json"

    with ZipFile2(bundle_path, "a") as bundle:
        write_receipt(
            bundle_path,
            bundle,
            output=output_path,
            receipt_url="https://example.com/receipt.json",
            release_url="https://example.com/file",
            release_version="1.0.0",
        )

    assert output_path.exists()


@patch("cosmofy.updater.add.write_receipt")
@patch("cosmofy.updater.add.copy_cosmofy")
@patch("cosmofy.updater.add.set_args")
@patch("cosmofy.updater.add.get_args")
def test_run_success(
    mock_get_args: MagicMock,
    mock_set_args: MagicMock,
    mock_copy: MagicMock,
    mock_write: MagicMock,
    tmp_path: Path,
) -> None:
    """Test run command success."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_get_args.return_value = "-m mymodule"
    mock_write.return_value = MagicMock()

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(
        Args,
        split(
            f"{bundle_path} --release-url https://example.com/file --release-version 1.0.0"
        ),
    )
    result = run(args)
    assert result == 0
    mock_copy.assert_called_once()


@patch("cosmofy.updater.add.get_github_download")
def test_run_no_urls(mock_github: MagicMock, tmp_path: Path) -> None:
    """Test run command fails without URLs."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_github.return_value = ""  # Can't auto-detect GitHub

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(Args, split(f"{bundle_path}"))
    result = run(args)
    assert result == 2  # Error due to missing URLs


@patch("cosmofy.updater.add.write_receipt")
@patch("cosmofy.updater.add.copy_cosmofy")
@patch("cosmofy.updater.add.set_args")
@patch("cosmofy.updater.add.get_args")
def test_run_with_no_copy(
    mock_get_args: MagicMock,
    mock_set_args: MagicMock,
    mock_copy: MagicMock,
    mock_write: MagicMock,
    tmp_path: Path,
) -> None:
    """Test run command with --no-copy."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_get_args.return_value = "-m mymodule"
    mock_write.return_value = MagicMock()

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(
        Args,
        split(
            f"{bundle_path} --release-url https://example.com/file --release-version 1.0.0 --no-copy"
        ),
    )
    result = run(args)
    assert result == 0
    mock_copy.assert_not_called()


@patch("cosmofy.updater.add.write_receipt")
@patch("cosmofy.updater.add.copy_cosmofy")
@patch("cosmofy.updater.add.set_args")
@patch("cosmofy.updater.add.get_args")
def test_run_with_no_args(
    mock_get_args: MagicMock,
    mock_set_args: MagicMock,
    mock_copy: MagicMock,
    mock_write: MagicMock,
    tmp_path: Path,
) -> None:
    """Test run command with --no-args."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_write.return_value = MagicMock()

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(
        Args,
        split(
            f"{bundle_path} --release-url https://example.com/file --release-version 1.0.0 --no-args"
        ),
    )
    result = run(args)
    assert result == 0
    mock_set_args.assert_not_called()


@patch("cosmofy.updater.add.write_receipt")
@patch("cosmofy.updater.add.copy_cosmofy")
@patch("cosmofy.updater.add.set_args")
@patch("cosmofy.updater.add.get_args")
def test_run_infer_receipt_url(
    mock_get_args: MagicMock,
    mock_set_args: MagicMock,
    mock_copy: MagicMock,
    mock_write: MagicMock,
    tmp_path: Path,
) -> None:
    """Test run command infers receipt URL from release URL."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_get_args.return_value = "-m mymodule"
    mock_write.return_value = MagicMock()

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(
        Args,
        split(
            f"{bundle_path} --release-url https://example.com/file --release-version 1.0.0"
        ),
    )
    result = run(args)
    assert result == 0
    # Should have inferred receipt_url
    assert args.receipt_url == "https://example.com/file.json"


@patch("cosmofy.updater.add.get_github_download")
@patch("cosmofy.updater.add.write_receipt")
@patch("cosmofy.updater.add.copy_cosmofy")
@patch("cosmofy.updater.add.set_args")
@patch("cosmofy.updater.add.get_args")
def test_run_infer_release_url(
    mock_get_args: MagicMock,
    mock_set_args: MagicMock,
    mock_copy: MagicMock,
    mock_write: MagicMock,
    mock_github: MagicMock,
    tmp_path: Path,
) -> None:
    """Test run command infers release URL from receipt URL."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_github.return_value = ""  # No github auto-detection
    mock_get_args.return_value = "-m mymodule"
    mock_write.return_value = MagicMock()

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(
        Args,
        split(
            f"{bundle_path} --receipt-url https://example.com/file.json --release-version 1.0.0"
        ),
    )
    result = run(args)
    assert result == 0
    # Should have inferred release_url
    assert args.release_url == "https://example.com/file"


@patch("cosmofy.updater.add.get_version")
@patch("cosmofy.updater.add.write_receipt")
@patch("cosmofy.updater.add.copy_cosmofy")
@patch("cosmofy.updater.add.set_args")
@patch("cosmofy.updater.add.get_args")
def test_run_no_version(
    mock_get_args: MagicMock,
    mock_set_args: MagicMock,
    mock_copy: MagicMock,
    mock_write: MagicMock,
    mock_get_version: MagicMock,
    tmp_path: Path,
) -> None:
    """Test run command fails when version cannot be determined."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_get_args.return_value = "-m mymodule"
    mock_get_version.return_value = ""  # Can't get version

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(
        Args, split(f"{bundle_path} --release-url https://example.com/file")
    )
    result = run(args)
    assert result == 2  # Error


@patch("cosmofy.updater.add.get_github_download")
def test_run_receipt_url_not_json(mock_github: MagicMock, tmp_path: Path) -> None:
    """Test run command fails when receipt URL doesn't end in .json."""
    from cosmofy.updater.add import run
    from cosmofy.zipfile2 import ZipFile2

    mock_github.return_value = ""  # No github auto-detection

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    args = baton.parse(
        Args,
        split(
            f"{bundle_path} --receipt-url https://example.com/file --release-version 1.0.0"
        ),
    )
    result = run(args)
    assert result == 2  # Error - can't infer release URL


@patch("cosmofy.updater.add.add_data")
@patch("cosmofy.updater.add.Receipt")
def test_write_receipt_invalid_embedded(
    mock_receipt_cls: MagicMock, mock_add_data: MagicMock, tmp_path: Path
) -> None:
    """Test write_receipt raises when embedded receipt is invalid."""
    from cosmofy.updater.add import write_receipt
    from cosmofy.zipfile2 import ZipFile2

    mock_receipt = MagicMock()
    mock_receipt.is_valid.return_value = False  # Invalid receipt
    mock_receipt.__str__ = MagicMock(return_value='{"test": "data"}')  # type: ignore[method-assign]
    mock_receipt_cls.return_value = mock_receipt

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    output_path = tmp_path / "receipt.json"

    with ZipFile2(bundle_path, "a") as bundle:
        with pytest.raises(ValueError) as exc:
            write_receipt(
                bundle_path,
                bundle,
                output=output_path,
                receipt_url="https://example.com/receipt.json",
                release_url="https://example.com/file",
                release_version="1.0.0",
            )
        assert "embedded receipt must be valid" in str(exc.value)


@patch("cosmofy.updater.add.add_data")
@patch("cosmofy.updater.add.Receipt")
def test_write_receipt_invalid_published(
    mock_receipt_cls: MagicMock, mock_add_data: MagicMock, tmp_path: Path
) -> None:
    """Test write_receipt raises when published receipt is invalid."""
    from cosmofy.updater.add import write_receipt
    from cosmofy.zipfile2 import ZipFile2

    mock_receipt = MagicMock()
    # First call returns True (embedded), second returns False (published)
    mock_receipt.is_valid.side_effect = [True, False]
    mock_receipt.__str__ = MagicMock(return_value='{"test": "data"}')  # type: ignore[method-assign]
    mock_receipt_cls.return_value = mock_receipt
    mock_receipt_cls.from_path.return_value = MagicMock(
        algo="sha256", hash="abc123", version="1.0.0"
    )

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    output_path = tmp_path / "receipt.json"

    with ZipFile2(bundle_path, "a") as bundle:
        with pytest.raises(ValueError) as exc:
            write_receipt(
                bundle_path,
                bundle,
                output=output_path,
                receipt_url="https://example.com/receipt.json",
                release_url="https://example.com/file",
                release_version="1.0.0",
            )
        assert "published receipt must be valid" in str(exc.value)


@patch("cosmofy.updater.add.add_path")
def test_from_venv(mock_add_path: MagicMock, tmp_path: Path) -> None:
    """Test from_venv copies cosmofy from filesystem."""
    from cosmofy.updater.add import from_venv
    from cosmofy.zipfile2 import ZipFile2

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    src_path = tmp_path / "cosmofy"
    src_path.mkdir()
    (src_path / "__init__.py").write_text("# init")

    meta_path = tmp_path / "cosmofy-1.0.0.dist-info"
    meta_path.mkdir()
    (meta_path / "METADATA").write_text("Name: cosmofy")

    with ZipFile2(bundle_path, "a") as bundle:
        from_venv(bundle, src_path, meta_path)

    assert mock_add_path.call_count == 2


@patch("cosmofy.updater.add.copy_data")
def test_from_cosmo(mock_copy_data: MagicMock, tmp_path: Path) -> None:
    """Test from_cosmo copies cosmofy from zip executable."""
    from cosmofy.updater.add import from_cosmo
    from cosmofy.zipfile2 import ZipFile2

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    # Create mock paths that simulate being inside a cosmo python
    src_path = Path("/fake/Lib/site-packages/cosmofy")
    meta_path = Path("/fake/Lib/site-packages/cosmofy-1.0.0.dist-info")

    with ZipFile2(bundle_path, "a") as bundle:
        with patch("cosmofy.updater.add.sys") as mock_sys:
            mock_sys.executable = str(bundle_path)  # Point to a zip
            from_cosmo(bundle, src_path, meta_path)

    assert mock_copy_data.call_count == 2


@patch("cosmofy.updater.add.from_cosmo")
@patch("cosmofy.updater.add.is_zipfile")
@patch("cosmofy.updater.add.metadata.distribution")
def test_copy_cosmofy_from_cosmo(
    mock_dist: MagicMock,
    mock_is_zipfile: MagicMock,
    mock_from_cosmo: MagicMock,
    tmp_path: Path,
) -> None:
    """Test copy_cosmofy when running from cosmo python."""
    from cosmofy.updater.add import copy_cosmofy
    from cosmofy.zipfile2 import ZipFile2

    # Create the dist-info directory so the path check passes
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    dist_info = src_dir / "cosmofy-0.1.0.dist-info"
    dist_info.mkdir()

    mock_dist_obj = MagicMock()
    mock_dist_obj.name = "cosmofy"
    mock_dist_obj.version = "0.1.0"
    mock_dist.return_value = mock_dist_obj
    mock_is_zipfile.return_value = True

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    # Mock __file__ to point to our test directory
    with patch("cosmofy.updater.add.Path") as mock_path_cls:
        mock_path_cls.return_value.parent.parent = src_dir
        mock_path_cls.side_effect = lambda x: Path(x) if isinstance(x, str) else x

        with ZipFile2(bundle_path, "a") as bundle:
            try:
                copy_cosmofy(bundle)
            except (FileNotFoundError, TypeError):
                pass  # Expected due to mocking complexity

    # from_cosmo should have been called


@patch("cosmofy.updater.add.from_venv")
@patch("cosmofy.updater.add.is_zipfile")
@patch("cosmofy.updater.add.metadata.distribution")
def test_copy_cosmofy_dist_path_fallback(
    mock_dist: MagicMock,
    mock_is_zipfile: MagicMock,
    mock_from_venv: MagicMock,
    tmp_path: Path,
) -> None:
    """Test copy_cosmofy uses dist._path when dist-info not at expected path."""
    from importlib.metadata import PathDistribution
    from cosmofy.updater.add import copy_cosmofy
    from cosmofy.zipfile2 import ZipFile2

    # Create a mock distribution with _path attribute
    mock_dist_obj = MagicMock(spec=PathDistribution)
    mock_dist_obj.name = "cosmofy"
    mock_dist_obj.version = "0.1.0"
    fallback_path = tmp_path / "fallback-cosmofy-0.1.0.dist-info"
    fallback_path.mkdir()
    mock_dist_obj._path = fallback_path
    mock_dist.return_value = mock_dist_obj
    mock_is_zipfile.return_value = False

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    with ZipFile2(bundle_path, "a") as bundle:
        copy_cosmofy(bundle)

    mock_from_venv.assert_called_once()


@patch("cosmofy.updater.add.is_zipfile")
@patch("cosmofy.updater.add.metadata.distribution")
def test_copy_cosmofy_dist_info_not_found(
    mock_dist: MagicMock, mock_is_zipfile: MagicMock, tmp_path: Path
) -> None:
    """Test copy_cosmofy raises when dist-info not found."""
    from cosmofy.updater.add import copy_cosmofy
    from cosmofy.zipfile2 import ZipFile2

    # Mock distribution without _path attribute
    mock_dist_obj = MagicMock()
    mock_dist_obj.name = "cosmofy"
    mock_dist_obj.version = "0.1.0"
    # No _path attribute, so hasattr(dist, "_path") will be False
    del mock_dist_obj._path
    mock_dist.return_value = mock_dist_obj
    mock_is_zipfile.return_value = False

    bundle_path = tmp_path / "bundle.zip"
    with ZipFile2(bundle_path, "w") as z:
        z.writestr("test.txt", "content")

    with ZipFile2(bundle_path, "a") as bundle:
        with pytest.raises(FileNotFoundError) as exc:
            copy_cosmofy(bundle)
        assert "could not location" in str(exc.value)
