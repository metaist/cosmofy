# pkg
from cosmofy import __main__ as root_main


def test_root_main() -> None:
    root_main.run(root_main.Args())
    root_main.run(root_main.Args(version=True))

    root_main.cmd.main(["--unknown"])

    root_main.setup_logger()
