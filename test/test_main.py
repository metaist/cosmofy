# std
from unittest.mock import MagicMock
from unittest.mock import patch

# pkg
from cosmofy import __main__ as root_main


def test_root_main() -> None:
    root_main.run(root_main.Args())
    root_main.run(root_main.Args(version=True))

    root_main.cmd.main(["--unknown"])

    root_main.setup_logger()


@patch.object(root_main, "cmd")
@patch("sys.exit")
def test_main_entry_point(mock_exit: MagicMock, mock_cmd: MagicMock) -> None:
    """Test main() entry point function."""
    mock_cmd.main.return_value = 0
    root_main.main()
    mock_exit.assert_called_once_with(0)
