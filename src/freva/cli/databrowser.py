from __future__ import annotations

import argparse
import sys
from typing import Any, Optional

import lazy_import
import rich

from evaluation_system import __version__
from evaluation_system.misc import logger

from .utils import BaseCompleter, BaseParser, standard_main

freva = lazy_import.lazy_module("freva")


class Cli(BaseParser):
    """Class that constructs the Databrowser Argument Parser."""

    desc = "Find data in the system."

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the databrowser sub arg. parser."""
        super().__init__(parser, "freva-databrowser")
        self.parser.add_argument(
            "--multiversion",
            default=False,
            action="store_true",
            help="Select not only the latest version.",
        )
        self.parser.add_argument(
            "--batch-size",
            default=5000,
            type=int,
            help="Number of files to retrieve.",
        )
        self.parser.add_argument(
            "--count",
            default=False,
            action="store_true",
            help="Show the number of files for each search result.",
        )
        self.parser.add_argument(
            "--facet",
            default=None,
            type=str,
            action="append",
            help=("Retrieve values of given facet instead of files."),
        )
        self.parser.add_argument(
            "--facet-limit",
            type=int,
            help="Limit the number of output facets.",
            default=sys.maxsize,
        )
        self.parser.add_argument(
            "--time-select",
            type=str,
            help="Operator that specifies how the time period is selected.",
            choices=["flexible", "strict", "file"],
            default="flexible",
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
            "facets",
            nargs="*",
            help="Search facet(s).",
            type=str,
            metavar="facets",
        )
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace,
        **kwargs: Optional[Any],
    ) -> None:
        """Call the databrowser command and print the results."""
        facets: dict[str, Any] = BaseCompleter.arg_to_dict(args.facets, append=True)
        facet_limit = kwargs.pop("facet_limit")
        for key in (
            "facets",
            "facet",
            "count",
            "relevant_only",
            "batch_size",
        ):
            _ = kwargs.pop(key, "")
        for key, values in facets.items():
            if len(values) == 1:
                facets[key] = values[0]
        merged_args: dict[str, Any] = {**kwargs, **facets}
        if args.count:
            out = freva.count_values(facet=args.facet, **merged_args)
        elif args.facet:
            out = freva.facet_search(facet=args.facet, **merged_args)
        else:
            out = freva.databrowser(batch_size=args.batch_size, **merged_args)
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
        if args.count:
            print(out, flush=True)
        else:
            for key in out:
                print(str(key), flush=True)


def main(argv: Optional[list[str]] = None) -> None:
    standard_main(Cli, __version__, argv)
