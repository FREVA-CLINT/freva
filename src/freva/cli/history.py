from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

import lazy_import
import rich

from evaluation_system import __version__
from evaluation_system.misc import logger

from .utils import BaseParser

freva = lazy_import.lazy_module("freva")


class Cli(BaseParser):
    """Class that constructs the History Query Parser."""

    desc = "Read the plugin application history."

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the history sub arg. parser."""
        super().__init__(parser, "freva-history")
        self.parser.add_argument(
            "--full-text",
            default=False,
            action="store_true",
            help="Show the complete configuration.",
        )
        self.parser.add_argument(
            "--return-command",
            default=False,
            action="store_true",
            help=(
                "Show freva commands belonging to the history entries "
                "instead of the entries themself."
            ),
        )
        self.parser.add_argument(
            "--limit",
            default=10,
            type=int,
            help="Limit the number of displayed entries to N",
        )
        self.parser.add_argument(
            "--plugin",
            default=None,
            type=str,
            help="Display only entries of selected plugin.",
        )
        self.parser.add_argument(
            "--since",
            default=None,
            type=str,
            help="Retrieve entries older than date",
        )
        self.parser.add_argument(
            "--until",
            default=None,
            type=str,
            help="Retrieve entries newer than date",
        )
        self.parser.add_argument(
            "--entry-ids",
            default=None,
            type=str,
            nargs="+",
            help="Select entry id(s) (e.g. --entry-ids 1 --entry-ids 2 )",
        )
        self.parser.add_argument(
            "--debug",
            "-v",
            "-d",
            "--verbose",
            help="Use verbose output.",
            action="store_true",
            default=False,
        )
        self.parser.add_argument(
            "--json",
            "-j",
            help=(
                "Display a json representation of the output, this can be"
                "useful if you want to build shell based pipelines and want"
                "parse the output with help of `jq`."
            ),
            action="store_true",
            default=False,
        )

        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace,
        **kwargs: Any,
    ) -> None:
        """Call the databrowser command and print the results."""
        kwargs.pop("other_args", "")
        return_json = kwargs.pop("json", False)
        if return_json:
            kwargs["return_results"] = True
        try:
            if len(kwargs["entry_ids"]) == 1:
                kwargs["entry_ids"] = kwargs["entry_ids"][0].split(",")
        except TypeError:
            pass
        commands = freva.history(_return_dict=return_json, **kwargs)
        if not commands and return_json is False:
            return
        if args.return_command and return_json is False:
            result = "\n".join(commands)
        elif return_json is True:
            result = json.dumps(commands, indent=3)
        else:
            result = "\n".join(
                [c.__str__(compact=not args.full_text) for c in commands]
            )
        print(result)


def main(argv: Optional[list[str]] = None) -> None:
    """Wrapper for entry point script."""
    cli = Cli()
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
        rich.print("[b]KeyboardInterrupt, exiting[/b]", file=sys.stderr, flush=True)
        sys.exit(130)
    except Exception as error:  # pragma: no cover
        freva.utils.exception_handler(error, True)  # pragma: no cover
