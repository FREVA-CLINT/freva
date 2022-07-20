from __future__ import annotations
import argparse
from pathlib import Path
import sys
from typing import Any, Optional


from evaluation_system import __version__
from evaluation_system.misc.exceptions import ValidationError
import freva
from .utils import BaseParser

CLI = "CrawlDataCli"


class CrawlDataCli(BaseParser):
    """Class that constructs the Data Crawler Argument Parser."""

    desc = "Update users project data"

    def __init__(
        self,
        command: str = "freva",
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the esgf sub arg. parser."""
        subparser = parser or argparse.ArgumentParser(
            prog=f"{command}-crawl-my-data",
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subparser.add_argument(
            "crawl_dir",
            nargs="*",
            type=Path,
            metavar="crawl_dir",
            help="The user directory(s) that needs to be crawled",
        )
        subparser.add_argument(
            "--data-type",
            "--dtype",
            default="fs",
            choices=["fs"],
            help="The data type of the data.",
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
    def run_cmd(args: argparse.Namespace, **kwargs: Any) -> None:
        """Call the crawl my data command and print the results."""
        try:
            freva.crawl_my_data(*args.crawl_dir, dtype=args.data_type)
        except (ValidationError, ValueError) as e:
            if args.debug:
                raise e
            try:
                print(f"{e.__module__}: " f"{e.__str__()}", flush=True, file=sys.stderr)
            except AttributeError:
                print(f"{e.__repr__()}", flush=True, file=sys.stderr)
            sys.exit(1)


def main(argv: Optional[list[str]] = None) -> None:
    """Wrapper for entry point script."""
    cli = CrawlDataCli("freva")
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
