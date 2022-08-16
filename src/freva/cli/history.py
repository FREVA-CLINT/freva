from __future__ import annotations
import argparse
import sys
from typing import Any, Optional

import lazy_import
from evaluation_system import __version__
from evaluation_system.misc import logger
from .utils import BaseParser

freva = lazy_import.lazy_module("freva")

CLI = "HistoryCli"


class HistoryCli(BaseParser):
    """Class that constructs the History Query Parser."""

    desc = "Read the plugin application history."

    def __init__(
        self,
        command: str = "freva",
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the history sub arg. parser."""
        subparser = parser or argparse.ArgumentParser(
            prog=f"{command}-history",
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subparser.add_argument(
            "--full-text",
            default=False,
            action="store_true",
            help="Show the complete configuration.",
        )
        subparser.add_argument(
            "--return-command",
            default=False,
            action="store_true",
            help=(
                "Show freva commands belonging to the history entries "
                "instead of the entries themself."
            ),
        )
        subparser.add_argument(
            "--limit",
            default=10,
            type=int,
            help="Limit the number of displayed entries to N",
        )
        subparser.add_argument(
            "--plugin",
            default=None,
            type=str,
            help="Display only entries of selected plugin.",
        )
        subparser.add_argument(
            "--since",
            default=None,
            type=str,
            help="Retrieve entries older than date",
        )
        subparser.add_argument(
            "--until",
            default=None,
            type=str,
            help="Retrieve entries newer than date",
        )
        subparser.add_argument(
            "--entry-ids",
            default=None,
            type=str,
            nargs="+",
            help="Select entry id(s) (e.g. --entry-ids 1 --entry-ids 2 )",
        )
        subparser.add_argument(
            "--debug",
            "-v",
            "-d",
            "--verbose",
            help="Use verbose output.",
            action="store_true",
            default=False,
        )
        self.parser = subparser
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace, other_args: Optional[list[str]], **kwargs: Any
    ) -> None:
        """Call the databrowser command and print the results."""
        kwargs.pop("other_args", "")
        try:
            if len(kwargs["entry_ids"]) == 1:
                kwargs["entry_ids"] = kwargs["entry_ids"][0].split(",")
        except TypeError:
            pass
        commands = freva.history(_return_dict=False, **kwargs)
        if not commands:
            return
        if args.return_command:
            result = "\n".join(commands)
        else:
            result = "\n".join(
                [c.__str__(compact=not args.full_text) for c in commands]
            )
        print(result)


def main(argv: Optional[list[str]] = None) -> None:
    """Wrapper for entry point script."""
    cli = HistoryCli("freva")
    cli.parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )
    args = cli.parse_args(argv or sys.argv[1:])
    try:
        cli.run_cmd(args, **cli.kwargs)
    except KeyboardInterrupt:  # pragma: no cover
        print("KeyboardInterrupt, exiting", file=sys.stderr, flush=True)
        sys.exit(130)
