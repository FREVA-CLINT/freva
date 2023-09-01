from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Type

import lazy_import
import rich

from evaluation_system import __version__
from evaluation_system.misc import logger

from .utils import BaseParser, SubCommandParser
from .user_data import AddData

futures = lazy_import.lazy_module("freva._futures")
freva = lazy_import.lazy_module("freva")

from evaluation_system.misc.exceptions import ValidationError


class RegisterFuture(AddData):
    """Add datasets to the databrowser that will be creased in the future."""

    desc = (
        "Add datasets to the databrowser that will be created in the "
        "future (future)."
    )

    def __init__(self, subparser: argparse.ArgumentParser):
        self.parser = subparser
        self.parser.add_argument(
            "future_definition",
            type=str,
            default=None,
            nargs="?",
            help="Name of the future definition.",
        )
        self.parser.add_argument(
            "--from-id",
            type=int,
            default=None,
            help=("Register a future dataset from a freva plugin history."),
        )
        self.parser.add_argument(
            "--variable-file",
            "-f",
            type=Path,
            default=None,
            help=(
                "Path to json file that holds additional variable definitions."
                "Variables that are databrowser search keys have to be added"
                "separately."
            ),
        )
        self.parser.add_argument(
            "--product",
            type=str,
            default=None,
            help="Set the <product> information.",
        )

        self._add_facets_to_parser(
            "Set <project> information",
            suffix="if the can't be found in the metadata",
        )
        self.parser.add_argument(
            "--time",
            type=str,
            default=None,
            help="Set the <time stamp> information.",
        )

        self.parser.add_argument(
            "--time-aggregation",
            type=str,
            default=None,
            help="Set the <time_aggregation> information.",
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
        self.parser.set_defaults(apply_func=self.run_cmd)

    def run_cmd(self, args: argparse.Namespace, **kwargs: str) -> None:
        """Run the futures command."""
        if args.from_id is not None:
            futures.Futures.register_future_from_history_id(args.from_id)
        else:
            if not args.future_definition:
                self.parser.error("You have to specify a future template.")
                raise SystemExit
            futures.Futures.register_future_from_template(
                args.future_definition,
                args.variable_file,
                project=args.project,
                product=args.product,
                experiment=args.experiment,
                institute=args.institute,
                variable=args.variable,
                time_frequency=args.time_frequency,
                ensemble=args.ensemble,
                realm=args.realm,
                time_aggregation=args.time_aggregation,
            )


class Cli(SubCommandParser):
    """Class that constructs the Future Argument Parser."""

    desc = "Register/list/update future datasets."

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the futures sub arg. parser."""
        subcommands: dict[str, Type[BaseParser]] = {
            "register": RegisterFuture,
        }
        super().__init__(
            parser, sub_parsers=subcommands, command="freva-user-data"
        )
        self.parser.set_defaults(apply_func=self._usage)

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs: str) -> None:
        args.apply_func(args, **kwargs)


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
        rich.print(
            "[b]KeyboardInterrupt, exiting[/b]", file=sys.stderr, flush=True
        )
        sys.exit(130)
    except Exception as error:  # pragma: no cover
        freva.utils.exception_handler(error, True)  # pragma: no cover
