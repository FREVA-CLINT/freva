"""General Freva commandline argument parser."""

import argparse
import sys
from typing import Optional, List

from evaluation_system import __version__
from .utils import BaseParser

COMMAND = "freva"


class ArgParser(BaseParser):
    """Cmd argument parser class for main entry-point."""

    def __init__(self, argv: List[str]):

        epilog = f"""To get help for the individual sub-commands use:
        {COMMAND} <sub-command> --help
"""
        argv = argv or sys.argv[1:]
        sub_parsers = self.get_subcommand_parsers()
        try:
            if argv[0].strip("-") in sub_parsers:
                argv[0] = argv[0].strip("-")
        except IndexError:
            argv.append("-h")
        parser = argparse.ArgumentParser(
            prog=COMMAND,
            epilog=epilog,
            description="Free EVAluation system framework (freva)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument(
            "-V",
            "--version",
            action="version",
            version="%(prog)s {version}".format(version=__version__),
        )
        super().__init__(sub_parsers, parser)
        args = self.parse_args(argv)
        try:
            args.apply_func(args, **self.kwargs)
        except KeyboardInterrupt:
            print("KeyboardInterrupt, exiting", file=sys.stderr, flush=True)
            sys.exit(130)


def main(argv: Optional[List[str]] = None) -> None:
    """Wrapper for entrypoint script."""
    ArgParser(argv or sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    main()
