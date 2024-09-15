"""Test `zipfile2` edge cases."""

# std
from unittest.mock import MagicMock
from unittest.mock import patch
from zipfile import ZipInfo
import io

# lib
import pytest

# pkg
from cosmofy.zipfile2 import ZipFile2


def test_errors() -> None:
    """Run time errors."""
    file = ZipFile2(io.BytesIO(), "a")  # to keep from `BadZipFile`

    file.mode = "r"
    with pytest.raises(RuntimeError):
        file.remove("fake")

    file.mode = "a"
    file._writing = True
    with pytest.raises(ValueError):
        file.remove("fake")

    file.mode = "a"
    file._writing = False
    file.close()
    with pytest.raises(ValueError):
        file.remove("fake")


@patch("cosmofy.zipfile2.ZipFile2._remove_member")
@patch("cosmofy.zipfile2.ZipFile2.getinfo")
def test_remove(_getinfo: MagicMock, _remove_member: MagicMock) -> None:
    """Test removing a member."""
    file = ZipFile2(io.BytesIO(), "a")  # to keep from `BadZipFile`
    info = ZipInfo("to_remove")

    file.remove(info)
    _remove_member.assert_called_once_with(info)

    file.remove("to_remove")
    assert _remove_member.called
    assert _getinfo.called

    file.remove("fake/*")
    assert _remove_member.called


def test_remove_real() -> None:
    """Remove actual members."""
    file = ZipFile2(io.BytesIO(), "a")

    file.writestr("real/keep1", b"to be kept")
    file.writestr("real/remove1", b"to be removed")
    file.writestr("real/keep2", b"to be kept")
    file.writestr("real/remove2", b"to be removed")
    assert len(file.filelist) == 4

    file.remove("real/remove2")
    file.remove("real/r*")
    assert len(file.filelist) == 2
