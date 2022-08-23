"""Collection of utilities of the freva command line argument parser."""

from __future__ import annotations
import argparse
from configparser import ConfigParser, ExtendedInterpolation
from copy import copy
from getpass import getuser
import logging
from pathlib import Path
from typing import Callable, Optional

import lazy_import
from evaluation_system.misc import logger

freva = lazy_import.lazy_module("freva")
config = lazy_import.lazy_module("evaluation_system.misc.config")

subparser_func_type = Callable[[argparse._SubParsersAction], Optional["BaseParser"]]
"""Type for a method that creates a sub-command parser. This method gets a string
representing the description of the sub command as well as the SubParserAction
this sub command parser is added to.
"""


def is_admin(raise_error: bool = False) -> bool:
    """Check if the user at runtime is one of the admins.

    Parameters:
    -----------
    raise_error:
        Raise a RuntimeError if user is not admin
    """
    config.reloadConfiguration()
    admin = [a for a in config.get("admins", "").split(",") if a.strip()]
    user = getuser()
    is_admin = user in admin
    if not is_admin and raise_error:
        raise RuntimeError(f"{user} is not in admin list")
    return is_admin


class BaseParser:
    """Base class for common command line argument parsers."""

    parser_func = argparse.ArgumentParser.parse_args
    """Define the standard arparse parsing function"""

    def __init__(
        self,
        sub_commands: dict[str, subparser_func_type],
        parser: argparse.ArgumentParser,
    ) -> None:
        """Create the sub-command parsers."""

        self.parser = parser
        self.subparsers = parser.add_subparsers(help="Available sub-commands:")
        self.help = self.get_subcommand_help()
        subcommands = self.get_subcommand_parsers()
        self.sub_commands = sub_commands
        for cmd, subparser in sub_commands.items():
            subparser(self.subparsers)

    @property
    def logger(self) -> logging.Logger:
        """Use evaluation_system logger in all classes using ths class."""
        return logger

    def set_debug(self, debug: bool) -> None:
        """Set the logger level to DEBUG."""
        if debug is True:
            self.logger.setLevel(logging.DEBUG)

    def parse_args(self, argv: Optional[list[str]] = None) -> argparse.Namespace:
        """Parse the command line arguments."""
        args, other_args = self.parser.parse_known_args(argv)
        self.kwargs = {k: v for (k, v) in args._get_kwargs() if k != "apply_func"}
        self.kwargs["other_args"] = other_args
        self.set_debug(self.kwargs.pop("debug", False))
        return args

    @staticmethod
    def parse_user_data(subparsers: argparse._SubParsersAction) -> None:
        """Parse the user data"""
        from .user_data import UserDataCli

        call_parsers = subparsers.add_parser(
            "user-data",
            help=UserDataCli.desc,
            description=UserDataCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        UserDataCli("freva", call_parsers)

    @staticmethod
    def parse_history(subparsers: argparse._SubParsersAction) -> None:
        """Parse the history command."""
        from .history import HistoryCli

        call_parser = subparsers.add_parser(
            "history",
            description=HistoryCli.desc,
            help=HistoryCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        HistoryCli("freva", call_parser)

    @staticmethod
    def parse_plugin(subparsers: argparse._SubParsersAction) -> None:
        """Parse the plugin command."""
        from .plugin import PluginCli

        call_parser = subparsers.add_parser(
            "plugin",
            help=PluginCli.desc,
            description=PluginCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        PluginCli("freva", call_parser)

    @staticmethod
    def parse_check(subparsers: argparse._SubParsersAction) -> None:
        """Parse the check command."""
        from .admin.check import CheckCli

        call_parser = subparsers.add_parser(
            "check",
            help=CheckCli.desc,
            description=CheckCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        CheckCli(call_parser)

    @staticmethod
    def parse_solr(subparsers: argparse._SubParsersAction) -> None:
        """Parse the solr index command."""
        from .admin.solr import SolrCli

        call_parser = subparsers.add_parser(
            "solr",
            help=SolrCli.desc,
            description=SolrCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        SolrCli(call_parser)

    @staticmethod
    def parse_doc(subparser: argparse._SubParsersAction) -> None:
        """Parse the docu update command."""
        from .admin.doc import DocCli

        call_parser = subparser.add_parser(
            "doc",
            help=DocCli.desc,
            description=DocCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        DocCli(call_parser)

    @staticmethod
    def parse_esgf(subparsers: argparse._SubParsersAction) -> None:
        """Parse the esgf command."""
        from .esgf import EsgfCli

        call_parsers = subparsers.add_parser(
            "esgf",
            help=EsgfCli.desc,
            description=EsgfCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        EsgfCli("freva", call_parsers)

    @staticmethod
    def parse_databrowser(subparsers: argparse._SubParsersAction) -> None:
        """Parse the databrowser command."""
        from .databrowser import DataBrowserCli

        call_parsers = subparsers.add_parser(
            "databrowser",
            description=DataBrowserCli.desc,
            help=DataBrowserCli.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        DataBrowserCli("freva", call_parsers)

    @classmethod
    def get_subcommand_parsers(cls) -> dict[str, subparser_func_type]:
        """Create the help strings of the available sub commands."""
        sub_commands: dict[str, subparser_func_type] = {
            "databrowser": cls.parse_databrowser,
            "plugin": cls.parse_plugin,
            "history": cls.parse_history,
            "user-data": cls.parse_user_data,
            "esgf": cls.parse_esgf,
        }
        admin_commands: dict[str, subparser_func_type] = {
            "solr": cls.parse_solr,
            "check": cls.parse_check,
            "doc": cls.parse_doc,
        }
        if is_admin():
            return {**sub_commands, **admin_commands}
        return sub_commands

    @classmethod
    def get_subcommand_help(cls) -> dict[str, str]:
        """Create the help strings of the available sub commands."""
        from freva.cli import user_data, databrowser, history, plugin, esgf

        modules = {
            "plugin": plugin,
            "databrowser": databrowser,
            "user-data": user_data,
            "history": history,
            "esgf": esgf,
        }
        return {h: getattr(mod, mod.CLI).desc for (h, mod) in modules.items()}

    def _usage(self, *args: Optional[str], **kwargs: Optional[str]) -> None:
        """Exit with usage message."""
        self.parser.error(
            "the following sub-commands are "
            f"required: {', '.join(self.sub_commands.keys())}"
        )


class BaseCompleter:
    """Base class for command line argument completers."""

    def __init__(
        self,
        metavar: str,
        argv: list[str],
        choices: Optional[dict[str, tuple[str, str]]] = None,
        shell: str = "bash",
        strip: bool = False,
        flags_only: bool = False,
    ):
        self.choices = choices or {}
        self.strip = strip
        self.metavar = metavar
        self.argv = argv
        self.flags_only = flags_only
        if shell == "zsh":
            self.get_print = self._print_zsh
        elif shell == "fish":
            self.get_print = self._print_fish
        else:
            self.get_print = self._print_default

    def _print_zsh(self, choices: dict[str, tuple[str, str]]) -> list[str]:
        out = []
        for key, (help, func) in choices.items():
            if self.metavar != "databrowser" or key.startswith("-"):
                out.append(f"{key}[{help}]{func}")
            else:
                out.append(f"{key}: {help}")
        return out

    def _print_fish(self, choices: dict[str, tuple[str, str]]) -> list[str]:
        out = []
        for key, (help, func) in choices.items():
            out.append(f"{key}: {help}")
        return out

    def _print_default(self, choices: dict[str, tuple[str, str]]) -> list[str]:

        out = []
        for key, (help, func) in choices.items():
            if self.metavar == "databrowser" and not key.startswith("-"):
                out.append(f"{key}: {help}")
            else:
                out.append(key)
        return out

    def _get_databrowser_choices(self) -> dict[str, tuple[str, str]]:
        """Get the choices for databrowser command."""

        facet_args = []
        for arg in self.argv:
            try:
                key, value = arg.split("=")
            except ValueError:
                continue
            facet_args.append(arg)
        facets = BaseCompleter.arg_to_dict(facet_args)
        search = freva.databrowser(attributes=False, all_facets=True, **facets)
        choices = {}
        for att, values in search.items():
            if att not in facets:
                keys = ",".join([v for n, v in enumerate(values)])
                choices[att] = (keys, "")
        return choices

    def _get_plugin_choices(self) -> dict[str, tuple[str, str]]:
        """Get the choices for the plugin command."""

        docs: dict[str, dict[str, str]] = {}
        desc: dict[str, dict[str, str]] = {}
        plugins: dict[str, str] = {}
        try:
            plugin_cache = freva.read_plugin_cache()
        except Exception:
            plugin_cache = []
        for plugin in plugin_cache:
            plugins[plugin.name] = plugin.description
            docs[plugin.name] = {}
            desc[plugin.name] = {}
            for param, doc, value in plugin.parameters:
                desc[plugin.name][param] = doc
                docs[plugin.name][param] = value
        args = [arg for arg in self.argv if not arg.startswith("-") and arg != "plugin"]
        choices = {}
        if not args:
            # No plugin name was given
            return {pl: (help, "") for pl, help in plugins.items()}
        try:
            plugin_config = docs[args[0]]
            setup = desc[args[0]]
        except KeyError:
            # Wrong plugin name
            return {}
        options = []
        for key in plugin_config.keys():
            option_present = False
            for arg in args:
                if arg.startswith(f"{key}="):
                    option_present = True
                    break
            if not option_present:
                options.append(f"{key}=")
        for option in options:
            opt = option.strip("=")
            if "file" in setup[opt].lower() or "dir" in setup[opt].lower():
                choices[opt] = (setup[opt], ":file:_files")
            else:
                choices[opt] = (setup[opt], "")
        return choices

    @property
    def command_choices(self) -> dict[str, tuple[str, str]]:

        choices = {}
        if self.flags_only:
            return self.choices
        if self.metavar == "databrowser":
            choices = self._get_databrowser_choices()
        elif self.metavar == "plugin":
            choices = self._get_plugin_choices()
        return {**self.choices, **choices}

    def formated_print(self) -> None:
        """Print all choices to be processed by the shell completion function."""

        out = self.get_print(self.command_choices)
        for line in out:
            if line.startswith("-") and self.strip and not self.flags_only:
                continue
            elif not line.startswith("-") and self.flags_only:
                continue
            print(line)

    @staticmethod
    def arg_to_dict(
        args: Optional[list[str]], append: bool = False
    ) -> dict[str, list[str]]:
        """Convert a parsed arguments with key=value pairs to a dictionary.

        Parameters:
        ----------
        args:
            Collection of arguments that are converted to dict, the arguments
            should be of form key=value
        append:
            If a key occurs twice convert first value to list and append second
            value to list, the default behaviour is updating the entry with
            the second value
        Returns:
        --------
        dict: Dictionariy representation of key=value pairs
        """
        out_dict: dict[str, list[str]] = {}
        for arg in args or []:
            key, _, value = arg.partition("=")
            if append and key in out_dict:
                out_dict[key].append(value)
            else:
                out_dict[key] = [value]
        return out_dict

    @classmethod
    def _get_choices_from_parser(
        cls,
        parser: argparse.ArgumentParser,
        argv: list[str],
    ) -> dict[str, tuple[str, str]]:
        choices: dict[str, tuple[str, str]] = {}
        for action in parser._actions:
            action_type = ""
            if isinstance(action, argparse._SubParsersAction):
                if argv:
                    cmd = argv.pop(0)
                    sub_parser = action.choices.get(cmd, "")
                    if sub_parser:
                        choices.update(cls._get_choices_from_parser(sub_parser, argv))
                else:
                    for ch, parser in action.choices.items():
                        choices[ch] = parser.description or "", action_type
            if action.help == argparse.SUPPRESS:
                # This is an option that is not exposed to users
                continue
            if action.type == Path:
                action_type = ":file:_files"
            if action.option_strings:
                choice = action.option_strings[0]
            else:
                choice = action.dest
            if choice.lower() not in (
                "facet",
                "facets",
                "tool-name",
                "options",
                "==suppress==",
                "-h",
            ):
                choices[choice] = (action.help or "", action_type)
        return choices

    @classmethod
    def get_args_of_subcommand(cls, argv: list[str]) -> dict[str, tuple[str, str]]:
        """Get all possible arguments from a freva sub-command."""
        from freva.cli import user_data, databrowser, history, plugin, esgf

        sub_command = argv.pop(0)
        modules = {
            "plugin": plugin,
            "databrowser": databrowser,
            "user-data": user_data,
            "history": history,
            "esgf": esgf,
        }
        try:
            mod = modules[sub_command]
        except AttributeError:
            return {}
        CliParser = getattr(mod, mod.CLI)()
        return cls._get_choices_from_parser(CliParser.parser, argv)

    @classmethod
    def parse_choices(cls, argv: list[str]) -> BaseCompleter:
        """Create the completion choices from given cmd arguments."""
        parser = argparse.ArgumentParser(
            description="Get choices for command line arguments"
        )
        parser.add_argument(
            "command", help="First command, freva, freva-histor etc", type=str
        )
        parser.add_argument("--shell", help="Shell in use", default="bash", type=str)
        parser.add_argument(
            "--strip",
            help="Do not print options starting with -",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--flags-only",
            help="Only print options starting with -",
            default=False,
            action="store_true",
        )
        ap, args = parser.parse_known_args(argv)
        main_choices = {k: (v, "") for k, v in BaseParser.get_subcommand_help().items()}
        if ap.command == "freva" and not args:
            return cls(ap.command, [], main_choices, shell=ap.shell, strip=ap.strip)
        elif ap.command != "freva":
            sub_cmd = "-".join(ap.command.split("-")[1:])
            args.insert(0, sub_cmd)
        choices = {}
        if args[0] in main_choices:
            choices = cls.get_args_of_subcommand(copy(args))
        choices = {k: v for (k, v) in choices.items() if k not in args}
        return cls(
            args[0],
            args,
            choices,
            shell=ap.shell,
            strip=ap.strip,
            flags_only=ap.flags_only,
        )


def print_choices(arguments: list[str]) -> None:
    """Print completion choices based of command line arguments.

    Parameters:
    -----------
    arguments:
        List of command line arguments, that are evaluated by the choice printer
    """
    argv = [arg.strip() for arg in arguments if arg.strip()]
    comp = BaseCompleter.parse_choices(argv)
    comp.formated_print()
