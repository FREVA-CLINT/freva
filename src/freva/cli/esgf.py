from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Union, cast

import lazy_import
import rich

from evaluation_system import __version__

from .utils import BaseParser
import json

freva = lazy_import.lazy_module("freva")
BaseCompleter = lazy_import.lazy_class("freva.cli.utils.BaseCompleter")


class Cli(BaseParser):
    """Class that constructs the ESGF Query Argument Parser."""

    desc = "Search/Download ESGF the data catalogue."

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the esgf sub arg. parser."""
        super().__init__(parser, "freva-esgf")
        self.parser = parser or argparse.ArgumentParser(
            prog="freva-esgf",
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self.parser.add_argument(
            "--datasets",
            default=False,
            action="store_true",
            help="List the name of the datasets instead of showing the urls.",
        )
        self.parser.add_argument(
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
        self.parser.add_argument(
            "--opendap",
            default=False,
            action="store_true",
            help="Show opendap endpoints instead of http ones.",
        )
        self.parser.add_argument(
            "--gridftp",
            default=False,
            action="store_true",
            help=(
                "Show gridftp endpoints instead of the http default "
                "ones (or skip them if none found)"
            ),
        )
        self.parser.add_argument(
            "--download-script",
            default=None,
            type=Path,
            help=(
                "Download wget_script for getting the files "
                "instead of displaying anything (only http) "
            ),
        )
        self.parser.add_argument(
            "--query",
            default=None,
            type=str,
            help=("Query fields from ESGF and group them per dataset"),
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
            help="Search facet(s)",
            type=str,
            metavar="facets",
        )
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace,
        other_args: Optional[list[str]] = None,
        **kwargs: Any,
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
        vars_to_pop = [
            "datasets",
            "download_script",
            "show_facet",
            "opendap",
            "gridftp",
            "query",
        ]
        if args.datasets:
            _ = [merged_args.pop(variable, "") for variable in vars_to_pop]
            out = freva.esgf_datasets(**merged_args)
            print("\n".join([f"{d[0]} - version: {d[1]}" for d in out]))
        elif args.show_facet:
            vars_to_pop.remove("show_facet")
            _ = [merged_args.pop(variable, "") for variable in vars_to_pop]
            out = freva.esgf_facets(**merged_args)
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
            vars_to_pop.remove("download_script")
            _ = [merged_args.pop(variable, "") for variable in vars_to_pop]
            out = freva.esgf_download(**merged_args)
            print(out)
        elif args.query:
            vars_to_pop.remove("query")
            _ = [merged_args.pop(variable, "") for variable in vars_to_pop]
            out = freva.esgf_query(**merged_args)
            if len(args.query.split(",")) > 1:
                print(json.dumps(out, indent=3))
            else:
                print("\n".join([str(d) for d in list(out)]))
        else:
            vars_to_pop.remove("opendap")
            vars_to_pop.remove("gridftp")
            _ = [merged_args.pop(variable, "") for variable in vars_to_pop]
            out = freva.esgf_browser(**merged_args)
            print("\n".join([str(d) for d in out]))


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
        rich.print("KeyboardInterrupt, exiting", file=sys.stderr, flush=True)
        sys.exit(130)
    except Exception as error:  # pragma: no cover
        freva.utils.exception_handler(error, True)  # pragma: no cover
