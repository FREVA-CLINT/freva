from __future__ import annotations
import argparse
from pathlib import Path
import sys
from typing import Any, Optional
import lazy_import


from evaluation_system import __version__
from evaluation_system.misc import logger
from .utils import BaseParser, BaseCompleter

freva = lazy_import.lazy_module("freva")
PluginNotFoundError = lazy_import.lazy_class(
    "evaluation_system.misc.exceptions.PluginNotFoundError"
)
ParameterNotFoundError = lazy_import.lazy_class(
    "evaluation_system.misc.exceptions.ParameterNotFoundError"
)
ValidationError = lazy_import.lazy_class(
    "evaluation_system.misc.exceptions.ValidationError"
)
hide_exception = lazy_import.lazy_function(
    "evaluation_system.misc.exceptions.hide_exception"
)


class Cli(BaseParser):
    """Class that constructs the Plugin Argument Parser."""

    desc = "Apply data analysis plugin."

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
    ):
        """Construct the plugin sub arg. parser."""
        super().__init__(parser, "freva-plugin")
        self.parser.add_argument(
            "tool-name",
            nargs="?",
            metavar="plugin_name",
            help="Plugin name",
            default=None,
        )
        self.parser.add_argument(
            "--repo-version",
            default=False,
            action="store_true",
            help="Show the version number from the repository",
        )
        self.parser.add_argument(
            "--caption",
            default="",
            help="Set a caption for the results",
        )
        self.parser.add_argument(
            "--save",
            default=False,
            action="store_true",
            help="Save the plugin configuration to default destination.",
        )
        self.parser.add_argument(
            "--save-config",
            type=Path,
            default=None,
            help="Save the plugin configuration.",
        )
        self.parser.add_argument(
            "--show-config",
            help="Show the resulting configuration (implies dry-run).",
            action="store_true",
            default=False,
        )
        self.parser.add_argument(
            "--scheduled-id",
            default=None,
            type=int,
            help=argparse.SUPPRESS,
        )
        self.parser.add_argument(
            "--dry-run",
            default=False,
            action="store_true",
            help="Perform no computation. Useful for development.",
        )
        self.parser.add_argument(
            "--batchmode",
            help="Create a Batch job and submit it to the scheduling system.",
            default=False,
            action="store_true",
        )
        self.parser.add_argument(
            "--unique_output",
            help="Append a freva run id to every output folder",
            default=True,
            type=bool,
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
            "--list-tools",
            "--list",
            "-l",
            default=False,
            action="store_true",
            help="Only list the available tools.",
        )
        self.parser.add_argument(
            "--doc",
            "--plugin-doc",
            default=False,
            action="store_true",
            help="Display plugin documentation",
        )
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace,
        other_args: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Call the databrowser command and print the results."""
        tool_name = kwargs.pop("tool-name")
        if kwargs.pop("list_tools") or not tool_name:
            print(freva.get_tools_list())
            return
        options: dict[str, Any] = BaseCompleter.arg_to_dict(other_args or [])
        for key, val in options.items():
            if len(val) == 1:
                options[key] = val[0]
        tool_args = {**kwargs, **options}
        try:
            if tool_args.pop("doc"):
                print(freva.plugin_doc(tool_name))
                return
            value, out = freva.run_plugin(tool_name or "", **tool_args)
        except (
            PluginNotFoundError,
            ValidationError,
            ParameterNotFoundError,
        ) as e:
            if args.debug:
                raise e
            with hide_exception():
                raise e
        if value != 0:
            logger.warning("Tool failed to run")
        if out:
            print(out)


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
