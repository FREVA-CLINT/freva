from __future__ import annotations
import argparse
from pathlib import Path
import sys
from typing import Any, Optional, Type

import lazy_import
from evaluation_system import __version__
from evaluation_system.misc import logger
from .utils import BaseParser, SubCommandParser

UserData = lazy_import.lazy_class("freva.UserData")
from evaluation_system.misc.exceptions import ValidationError


class IndexData(BaseParser):
    """CLI class that deals with indexing the data."""

    desc = "Index existing user project data to the databrowser"

    def __init__(self, subparser: argparse.ArgumentParser):
        super().__init__(subparser)
        self.parser.add_argument(
            "crawl_dir",
            nargs="*",
            type=Path,
            metavar="crawl_dir",
            help="The user directory(s) that needs to be crawled.",
        )
        self.parser.add_argument(
            "--data-type",
            "--dtype",
            default="fs",
            choices=["fs"],
            help="The data type of the data.",
        )
        self.parser.add_argument(
            "--continue-on-errors",
            "--continue",
            "-c",
            action="store_true",
            help="Continue indexing on error.",
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

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs: Any) -> None:
        """Call the crawl my data command and print the results."""
        user_data = UserData()
        try:
            user_data.index(
                *args.crawl_dir,
                dtype=args.data_type,
                continue_on_errors=args.continue_on_errors,
            )
        except (ValidationError, ValueError) as e:
            if args.debug:
                raise e
            try:
                print(
                    f"{e.__module__}: " f"{e.__str__()}",
                    flush=True,
                    file=sys.stderr,
                )
            except AttributeError:
                print(f"{e.__repr__()}", flush=True, file=sys.stderr)
            sys.exit(1)


class AddData(BaseParser):
    """CLI class that deals with indexing the data."""

    desc = "Add new user project data to the databrowser"

    def __init__(self, subparser: argparse.ArgumentParser):
        super().__init__(subparser)
        self.parser.add_argument(
            "product",
            type=str,
            help="Product search key the newly added data can be found.",
        )
        self.parser.add_argument(
            "paths",
            nargs="+",
            type=Path,
            metavar="paths",
            help=(
                "Filename(s) or Directories that are going to be added to the"
                "databrowser"
            ),
        )
        self.parser.add_argument(
            "--how",
            default="copy",
            choices=["copy", "move", "symlink", "link"],
            help=(
                "Method of how the data is added into the central freva user "
                "directory."
            ),
        )
        self.parser.add_argument(
            "--override",
            "--overwrite",
            action="store_true",
            help="Replace existing files in the user data structre",
            default=False,
        )
        self.parser.add_argument(
            "--experiment",
            type=str,
            default=None,
            help=(
                "Set the <experiment> information if they can't be found in the "
                "meta data"
            ),
        )
        self.parser.add_argument(
            "--institute",
            type=str,
            default=None,
            help=(
                "Set the <institute> information if they can't be found in the "
                "meta data"
            ),
        )
        self.parser.add_argument(
            "--model",
            type=str,
            default=None,
            help=(
                "Set the <model> information if they can't be found in the " "meta data"
            ),
        )
        self.parser.add_argument(
            "--variable",
            type=str,
            default=None,
            help=(
                "Set the <variable> information if they can't be found in the "
                "meta data"
            ),
        )
        self.parser.add_argument(
            "--time_frequency",
            type=str,
            default=None,
            help=(
                "Set the <time_frequency> information if they can't be found in the "
                "meta data"
            ),
        )
        self.parser.add_argument(
            "--ensemble",
            type=str,
            default=None,
            help=(
                "Set the <ensemble> information if they can't be found in the "
                "meta data"
            ),
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

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs: Any) -> None:
        """Call the crawl my data command and print the results."""
        facets = (
            "experiment",
            "institute",
            "model",
            "variable",
            "time_frequency",
            "ensemble",
        )
        defaults = {k: getattr(args, k) for k in facets if getattr(args, k)}
        user_data = UserData()
        try:
            user_data.add(
                args.product,
                *args.paths,
                how=args.how,
                override=args.override,
                **defaults,
            )
        except (ValidationError, ValueError) as e:
            if args.debug:
                raise e
            logger.error("%s", e)
            sys.exit(1)


class DeleteData(BaseParser):
    """CLI class that deals with indexing the data."""

    desc = "Delete existing user project data from the databrowser"

    def __init__(self, subparser: argparse.ArgumentParser):
        self.parser = subparser
        self.parser.add_argument(
            "paths",
            nargs="+",
            type=Path,
            metavar="paths",
            help="The user directory(s) that needs to be crawled",
        )
        self.parser.add_argument(
            "--delete-from-fs",
            "--delete_from_fs",
            "--delete",
            action="store_true",
            default=False,
            help=(
                "Do not only delete the files from the databrowser but also "
                "from file system."
            ),
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

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs: Any) -> None:
        """Call the crawl my data command and print the results."""
        user_data = UserData()
        user_data.delete(*args.paths, delete_from_fs=args.delete_from_fs)


class Cli(SubCommandParser):
    """Class that constructs the Data Crawler Argument Parser."""

    desc = "Update users project data"

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the esgf sub arg. parser."""
        subcommands: dict[str, Type[BaseParser]] = {
            "index": IndexData,
            "add": AddData,
            "delete": DeleteData,
        }
        super().__init__(parser, sub_parsers=subcommands, command="freva-user-data")
        self.parser.set_defaults(apply_func=self._usage)

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs: str):
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
        print("KeyboardInterrupt, exiting", file=sys.stderr, flush=True)
        sys.exit(130)
