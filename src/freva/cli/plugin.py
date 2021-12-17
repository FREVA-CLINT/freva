import argparse
from pathlib import Path
import sys
from typing import Optional, List

import argcomplete

from .utils import BaseCompleter, BaseParser, parse_type
from evaluation_system.misc.exceptions import (
    PluginNotFoundError,
    ParameterNotFoundError,
    ValidationError,
    hide_exception,
)
from evaluation_system.misc import logger
from freva._plugin import get_tools_list, run_plugin, plugin_doc


class PluginCli(BaseParser):
    """Class that constructs the Plugin Argument Parser."""

    desc = "Apply data analysis plugin."

    def __init__(
        self,
        command: str = "freva",
        parser: Optional[parse_type] = None,
    ):
        """Construct the plugin sub arg. parser."""
        subparser = parser or argparse.ArgumentParser(
            prog=f"{command}-plugin",
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subparser.add_argument(
            "tool-name",
            nargs="?",
            metavar="plugin_name",
            help="Plugin name",
            default=None,
        )
        subparser.add_argument(
            "--repo-version",
            default=False,
            action="store_true",
            help="Show the version number from the repository",
        )
        subparser.add_argument(
            "--caption",
            default="",
            help="Set a caption for the results",
        )
        subparser.add_argument(
            "--save",
            default=False,
            action="store_true",
            help="Save the plugin configuration to default destination.",
        )
        subparser.add_argument(
            "--save-config",
            type=Path,
            default=None,
            help="Save the plugin configuration.",
        )
        subparser.add_argument(
            "--show-config",
            help="Show the resulting configuration (implies dry-run).",
            action="store_true",
            default=False,
        )
        subparser.add_argument(
            "--scheduled-id",
            default=None,
            type=int,
            help="Run a scheduled job from database",
        )
        subparser.add_argument(
            "--dry-run",
            default=False,
            action="store_true",
            help="Perform no computation. Useful for development.",
        )
        subparser.add_argument(
            "--batchmode",
            help="Create a Batch job and submit it to the scheduling system.",
            default=False,
            action="store_true",
        )
        subparser.add_argument(
            "--unique_output",
            help="Append a freva run id to every output folder",
            default=True,
            type=bool,
        )
        subparser.add_argument(
            "--pull-request",
            help="Issue a new pull request for the tool",
            default=False,
            action="store_true",
        )
        subparser.add_argument(
            "--tag", help="Use git commit hash", type=str, default=None
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
            "--list-tools",
            "--list",
            "-l",
            default=False,
            action="store_true",
            help="Only list the available tools.",
        )
        subparser.add_argument(
            "--doc",
            "--plugin-doc",
            default=False,
            action="store_true",
            help="Display plugin documentation",
        )
        subparser.add_argument(
            "options",
            nargs="*",
            help="Plugin configuration",
            type=str,
            metavar="options",
        )
        self.parser = subparser
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs):
        """Call the databrowser command and print the results."""
        options = BaseCompleter.arg_to_dict(args.options)
        if kwargs.pop("list_tools"):
            print(get_tools_list())
            return
        _ = kwargs.pop("options", None)
        tool_name = kwargs.pop("tool-name")
        try:
            if kwargs.pop("doc"):
                print(plugin_doc(tool_name))
                return
            value, out = run_plugin(tool_name, **kwargs, **options)
        except (PluginNotFoundError, ValidationError, ParameterNotFoundError) as e:
            if args.debug:
                raise e
            with hide_exception():
                raise e
        if value != 0:
            logger.warning("Tool failed to run")
        if out:
            print(out)


def main(argv: Optional[List[str]] = None) -> None:
    """Wrapper for entry point script."""
    cli = PluginCli("freva")
    args = cli.parse_args(argv or sys.argv[1:])
    options = BaseCompleter.arg_to_dict(args.options)
    argcomplete.autocomplete(cli.parser)
    try:
        cli.run_cmd(args, **cli.kwargs)
    except KeyboardInterrupt:
        sys.exit(1)
