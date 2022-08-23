from __future__ import annotations
import argparse
from pathlib import Path
import sys
from typing import Any, Optional

import lazy_import
from evaluation_system import __version__
from evaluation_system.misc import logger
from .utils import BaseParser, subparser_func_type

UserData = lazy_import.lazy_class("freva.UserData")
from evaluation_system.misc.exceptions import ValidationError

CLI = "UserDataCli"


class IndexData(BaseParser):
    """CLI class that deals with indexing the data."""

    desc = "Update user project data in the databrowser"

    def __init__(self, subparser: argparse.ArgumentParser):

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
        user_data = UserData()
        try:
            user_data.index(*args.crawl_dir, dtype=args.data_type)
        except (ValidationError, ValueError) as e:
            if args.debug:
                raise e
            try:
                print(f"{e.__module__}: " f"{e.__str__()}", flush=True, file=sys.stderr)
            except AttributeError:
                print(f"{e.__repr__()}", flush=True, file=sys.stderr)
            sys.exit(1)


class AddData(BaseParser):
    """CLI class that deals with indexing the data."""

    desc = "Add new user data to the the databrowser"

    def __init__(self, subparser: argparse.ArgumentParser):

        subparser.add_argument(
            "product",
            type=str,
            help="Product search key the newly added data can be found.",
        )
        subparser.add_argument(
            "paths",
            nargs="+",
            type=Path,
            metavar="paths",
            help=(
                "Filename(s) or Directories that are going to be added to the"
                "databrowser"
            ),
        )
        subparser.add_argument(
            "--how",
            default="copy",
            choices=["copy", "move", "symlink", "link"],
            help=(
                "Method of how the data is added into the central freva user "
                "directory."
            ),
        )
        subparser.add_argument(
            "--override",
            "--overwrite",
            action="store_true",
            help="Replace existing files in the user data structre",
            default=False,
        )
        subparser.add_argument(
            "--experiment",
            type=str,
            default=None,
            help=(
                "Set the <experiment> information if they can't be found in the "
                "meta data"
            ),
        )
        subparser.add_argument(
            "--institute",
            type=str,
            default=None,
            help=(
                "Set the <institute> information if they can't be found in the "
                "meta data"
            ),
        )
        subparser.add_argument(
            "--model",
            type=str,
            default=None,
            help=(
                "Set the <model> information if they can't be found in the " "meta data"
            ),
        )
        subparser.add_argument(
            "--variable",
            type=str,
            default=None,
            help=(
                "Set the <variable> information if they can't be found in the "
                "meta data"
            ),
        )
        subparser.add_argument(
            "--time_frequency",
            type=str,
            default=None,
            help=(
                "Set the <time_frequency> information if they can't be found in the "
                "meta data"
            ),
        )
        subparser.add_argument(
            "--ensemble",
            type=str,
            default=None,
            help=(
                "Set the <ensemble> information if they can't be found in the "
                "meta data"
            ),
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

    desc = "Delete user project data from the databrowser"

    def __init__(self, subparser: argparse.ArgumentParser):

        subparser.add_argument(
            "paths",
            nargs="+",
            type=Path,
            metavar="paths",
            help="The user directory(s) that needs to be crawled",
        )
        subparser.add_argument(
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
        user_data = UserData()
        user_data.delete(*args.paths, delete_from_fs=args.delete_from_fs)


class UserDataCli(BaseParser):
    """Class that constructs the Data Crawler Argument Parser."""

    desc = "Update users project data"

    def __init__(
        self,
        command: str = "freva",
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the esgf sub arg. parser."""
        subparser = parser or argparse.ArgumentParser(
            prog=f"{command}-user-data",
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subcommands: dict[str, subparser_func_type] = {
            "index": self.index,
            "add": self.add,
            "delete": self.delete,
        }
        super().__init__(subcommands, subparser)
        self.parser.set_defaults(apply_func=self._usage)

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs: str):
        args.apply_func(args, **kwargs)

    @staticmethod
    def index(subparsers: argparse._SubParsersAction) -> IndexData:
        sub_parser = subparsers.add_parser(
            "index",
            description="Index existing user project data to the databrowser",
            help="Index existing user project data to the databrowser",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        return IndexData(sub_parser)

    @staticmethod
    def add(subparsers: argparse._SubParsersAction) -> AddData:
        help = "Add new user project data to the databrowser"
        sub_parser = subparsers.add_parser(
            "add",
            description=help,
            help=help,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        return AddData(sub_parser)

    @staticmethod
    def delete(subparsers: argparse._SubParsersAction) -> DeleteData:
        help = "Delete existing user project data from the databrowser"
        sub_parser = subparsers.add_parser(
            "delete",
            description=help,
            help=help,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        return DeleteData(sub_parser)


def main(argv: Optional[list[str]] = None) -> None:
    """Wrapper for entry point script."""
    cli = UserDataCli("freva")
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
