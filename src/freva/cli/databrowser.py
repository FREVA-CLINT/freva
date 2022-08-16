from __future__ import annotations
import argparse
import sys
from typing import Any, Optional

import lazy_import
from evaluation_system import __version__
from .utils import BaseParser, BaseCompleter

freva = lazy_import.lazy_module("freva")

CLI = "DataBrowserCli"


class DataBrowserCli(BaseParser):
    """Class that constructs the Databrowser Argument Parser."""

    desc = "Find data in the system."

    def __init__(
        self,
        command: str = "freva",
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the databrwoser sub arg. parser."""
        subparser = parser or argparse.ArgumentParser(
            prog=f"{command}-databrowser",
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subparser.add_argument(
            "--multiversion",
            default=False,
            action="store_true",
            help="Select not only the latest version.",
        )
        subparser.add_argument(
            "--relevant-only",
            default=False,
            action="store_true",
            help="Show only search with results >1 possible values",
        )
        subparser.add_argument(
            "--batch-size",
            default=5000,
            type=int,
            help="Number of files to retrieve",
        )
        subparser.add_argument(
            "--count",
            default=False,
            action="store_true",
            help="Show the number of files for each search result",
        )
        subparser.add_argument(
            "--attributes",
            default=False,
            action="store_true",
            help=(
                "Retrieve all possible attributes for the current "
                "search instead of the files."
            ),
        )
        subparser.add_argument(
            "--all-facets",
            default=False,
            action="store_true",
            help=("retrieve all facets (attributes & values) instead of " "the files"),
        )
        subparser.add_argument(
            "--facet",
            default=None,
            type=str,
            action="append",
            help=("Retrieve values of given facet instead of files"),
        )
        subparser.add_argument(
            "--facet-limit",
            type=int,
            help="Limit the number of output facets.",
            default=sys.maxsize,
        )
        subparser.add_argument(
            "--time-select",
            type=str,
            help="Operator that specifies how the time period is selected.",
            choices=["flexible", "strict", "file"],
            default="flexible",
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
        subparser.add_argument(
            "facets", nargs="*", help="Search facet(s)", type=str, metavar="facets"
        )
        self.parser = subparser
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace,
        other_args: Optional[list[str]] = None,
        **kwargs: Optional[Any],
    ) -> None:
        """Call the databrowser command and print the results."""
        facets: dict[str, Any] = BaseCompleter.arg_to_dict(args.facets, append=True)
        facet_limit = kwargs.pop("facet_limit")
        _ = kwargs.pop("facets")
        for key, values in facets.items():
            if len(values) == 1:
                facets[key] = values[0]
        merged_args: dict[str, Any] = {**kwargs, **facets}
        out = freva.databrowser(**merged_args)
        # flush stderr in case we have something pending
        sys.stderr.flush()
        if isinstance(out, dict):
            # We have facet values as return values
            for att, values in out.items():
                facet_limit = facet_limit or len(values) + 1
                try:
                    keys = ",".join(
                        [
                            f"{k} ({c})"
                            for n, (k, c) in enumerate(values.items())
                            if n < facet_limit
                        ]
                    )
                except AttributeError:
                    keys = ",".join(
                        [v for n, v in enumerate(values) if n < facet_limit]
                    )
                if facet_limit < len(values):
                    keys += ",..."
                print(f"{att}: {keys}", flush=True)
            return
        if args.attributes:
            print(", ".join(out), flush=True)
            return
        if args.count:
            print(out, flush=True)
        else:
            for key in out:
                print(str(key), flush=True)


def main(argv: Optional[list[str]] = None) -> None:
    """Wrapper for entry point script."""
    cli = DataBrowserCli("freva")
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
