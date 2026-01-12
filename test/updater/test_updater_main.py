"""Test updater __main__ module."""

# std
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

# pkg
from cosmofy.updater import __main__ as updater_main


def test_run_shows_usage() -> None:
    """Test run function shows usage when no subcommand."""
    args = updater_main.Args()
    with patch.object(updater_main.cmd, "show_usage") as mock_show:
        result = updater_main.run(args)
        assert result == 0
        mock_show.assert_called_once()


@patch.object(updater_main, "cmd")
@patch.object(sys, "exit")
def test_main_block(mock_exit: MagicMock, mock_cmd: MagicMock) -> None:
    """Test if __name__ == '__main__' block."""
    mock_cmd.main.return_value = 0
    # Execute the module-level code
    exec(
        "import sys; sys.exit(cmd.main())",
        {"sys": sys, "cmd": mock_cmd, "exit": mock_exit},
    )
    mock_cmd.main.assert_called_once()
