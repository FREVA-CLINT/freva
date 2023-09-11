"""General Freva commandline argument parser."""

import argparse
import sys
from typing import List, Optional

import lazy_import
from rich import print

from evaluation_system import __version__

from .utils import SubCommandParser

freva = lazy_import.lazy_module("freva")

COMMAND = "freva"


class ArgParser(SubCommandParser):
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
        super().__init__(parser, sub_parsers)
        args = self.parse_args(argv)
        try:
            args.apply_func(args, **self.kwargs)
        except KeyboardInterrupt:
            print(
                "[b]KeyboardInterrupt, exiting[/b]",
                file=sys.stderr,
                flush=True,
            )
            sys.exit(130)
        except Exception as error:  # pragma: no cover
            freva.utils.exception_handler(error, True)  # pragma: no cover


def main(argv: Optional[List[str]] = None) -> None:
    """Wrapper for entrypoint script."""
    ArgParser(argv or sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    main()
