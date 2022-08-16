from __future__ import annotations
import argparse
from pathlib import Path
import sys
from typing import Optional, Any, cast, Union

import lazy_import
from evaluation_system import __version__
from .utils import BaseParser

freva = lazy_import.lazy_module("freva")
BaseCompleter = lazy_import.lazy_class("freva.cli.utils.BaseCompleter")

CLI = "EsgfCli"


class EsgfCli(BaseParser):
    """Class that constructs the ESGF Query Argument Parser."""

    desc = "Search/Download ESGF the data catalogue."

    def __init__(
        self,
        command: str = "freva",
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the esgf sub arg. parser."""
        subparser = parser or argparse.ArgumentParser(
            prog=f"{command}-esgf",
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subparser.add_argument(
            "--datasets",
            default=False,
            action="store_true",
            help="List the name of the datasets instead of showing the urls.",
        )
        subparser.add_argument(
            "--show-facet",
            default=None,
            action="append",
            help=(
                "List all values for the given facet (might be "
                "defined multiple times). The results show the possible "
                "values of the selected facet according to the given "
                "constraints and the number of *datasets* (not files) "
                "that selecting such value as a constraint will result "
                "(faceted search)"
            ),
        )
        subparser.add_argument(
            "--opendap",
            default=False,
            action="store_true",
            help="Show opendap endpoints instead of http onse.",
        )
        subparser.add_argument(
            "--gridftp",
            default=False,
            action="store_true",
            help=(
                "Show gridftp endpoints instead of the http default "
                "ones (or skip them if none found)"
            ),
        )
        subparser.add_argument(
            "--download-script",
            default=None,
            type=Path,
            help=(
                "Download wget_script for getting the files "
                "instead of displaying anything (only http) "
            ),
        )
        subparser.add_argument(
            "--query",
            default=None,
            type=str,
            help=("Display results from <list> queried fields"),
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
        args: argparse.Namespace, other_args: Optional[list[str]] = None, **kwargs: Any
    ) -> None:
        """Call the esgf command and print the results."""
        facets: dict[str, Union[list[str], str]] = {}
        _facets = BaseCompleter.arg_to_dict(args.facets)
        _ = kwargs.pop("facets", None)
        for key, val in _facets.items():
            if len(val) == 1:
                facets[key] = val[0]
            else:
                facets[key] = val
        merged_args = cast(Any, {**kwargs, **facets})
        out = freva.esgf(**merged_args)
        if not out:
            return
        if args.datasets:
            print("\n".join([f"{d[0]} - version: {d[1]}" for d in out]))
        elif args.query:
            if len(args.query.split(",")) > 1:
                print("\n".join([str(out)]))
            else:
                print("\n".join([str(d) for d in list(out)]))
        elif args.show_facet:
            for facet_key in sorted(out):
                if len(out[facet_key]) == 0:
                    values = "<No Results>"
                else:
                    values = "\n\t".join(
                        [
                            "%s: %s" % (k, out[facet_key][k])
                            for k in sorted(out[facet_key])
                        ]
                    )
                    print("[%s]\n\t%s" % (facet_key, values))
        elif args.download_script:
            print(out)
        else:
            print("\n".join([str(d) for d in out]))


def main(argv: Optional[list[str]] = None) -> None:
    """Wrapper for entry point script."""
    cli = EsgfCli("freva")
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
