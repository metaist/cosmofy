# std
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch
import logging

# lib
import pytest

# pkg
from cosmofy import args


def test_banner() -> None:
    assert args.get_banner(True) == args.DRY_RUN
    assert args.get_banner(False) == ""


def test_global_args() -> None:
    have = args.GlobalArgs()
    assert have.for_real is not have.dry_run

    have.for_real = False
    assert have.dry_run is True
    assert have.banner == args.DRY_RUN


def test_setup_logger() -> None:
    have = args.GlobalArgs(quiet=1)
    have.setup_logger()
    have.show_error(logging.getLogger(), ValueError("key not found"))

    have = args.GlobalArgs(verbose=2)
    have.setup_logger()
    have.show_error(logging.getLogger(), ValueError("key not found"))


def test_common_args() -> None:
    have = args.CommonArgs(dry_run=True)
    assert have.ensure_bundle() is True, "dry run should still work"

    have = args.CommonArgs(bundle=Path("fake"), dry_run=True)
    assert have.ensure_bundle() is True

    with pytest.raises(FileNotFoundError):
        have = args.CommonArgs(bundle=Path("fake"))
        have.ensure_bundle()
