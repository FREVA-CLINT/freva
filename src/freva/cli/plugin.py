from __future__ import annotations

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from rich import print as pprint
from rich.console import Console

console = Console()
import lazy_import

from evaluation_system import __version__
from evaluation_system.misc import logger

from .utils import BaseCompleter, BaseParser, standard_main

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


@contextmanager
def _pipe(redirect_stdout: bool = False) -> Iterator[None]:
    """Redirect the stdout to stderr if needed."""

    stdout = sys.stdout
    try:
        if redirect_stdout is True:
            sys.stdout = sys.stderr
        yield
    finally:
        sys.stdout = stdout


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
            help="Plugin name.",
            default=None,
        )
        self.parser.add_argument(
            "--repo-version",
            default=False,
            action="store_true",
            help="Show the version number from the repository.",
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
            help="Show the resulting configuration.",
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
            "--batchmode",
            help="Create a Batch job and submit it to the scheduling system.",
            default=False,
            action="store_true",
        )
        self.parser.add_argument(
            "--unique-output",
            "--unique_output",
            choices=["true", "false", "True", "False"],
            help="Append a Freva run id to the output/cache folder(s).",
            default="true",
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
        self.parser.add_argument(
            "--json",
            "-j",
            help=(
                "Display a json representation of the result, this can be"
                "useful if you want to build shell based pipelines and want"
                "parse the output with help of `jq`."
            ),
            default=False,
            action="store_true",
        )
        self.parser.add_argument(
            "--wait",
            "-w",
            help=(
                "Wait for the plugin to finish, this has only an effect for "
                "batch mode execution."
            ),
            default=False,
            action="store_true",
        )

        self.parser.add_argument("tool-options", nargs="*", help="Tool options")
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace,
        **kwargs: Any,
    ) -> None:
        """Call the plugin command and print the results."""
        tool_name = kwargs.pop("tool-name")
        jsonify = kwargs.pop("json", False)
        wait = kwargs.pop("wait", False)
        tool_options = kwargs.pop("tool-options", []) + kwargs.pop("unknown", [])
        repo_version: bool = kwargs.pop("repo_version", False)
        show_config: bool = kwargs.pop("show_config", False)
        if kwargs.pop("list_tools") or not tool_name:
            console.print(freva.get_tools_list())
            return
        options: dict[str, Any] = BaseCompleter.arg_to_dict(tool_options)
        for key, val in options.items():
            if len(val) == 1:
                options[key] = val[0]
        if kwargs["unique_output"].lower() == "true":
            kwargs["unique_output"] = True
        else:
            kwargs["unique_output"] = False
        tool_args = {**kwargs, **options}
        value = 0
        try:
            if tool_args.pop("doc"):
                console.print(freva.plugin_doc(tool_name))
                return
            if repo_version:
                print(freva.plugin_info(tool_name or "", "repository", **options))
            elif show_config:
                print(freva.plugin_info(tool_name or "", "config", **options))
            else:
                with _pipe(redirect_stdout=jsonify):
                    plugin_run = freva.run_plugin(tool_name or "", **tool_args)
                value = int(plugin_run.status == "broken")
        except (
            PluginNotFoundError,
            ValidationError,
            ParameterNotFoundError,
        ) as e:
            if args.debug:
                raise e
            with hide_exception():
                logger.error(e)
                raise SystemExit
        if value != 0:
            logger.warning("Tool failed to run")
        elif jsonify or wait:
            plugin_run.wait()
        if jsonify:
            print(plugin_run)


def main(argv: Optional[list[str]] = None) -> None:
    standard_main(Cli, __version__, argv)
