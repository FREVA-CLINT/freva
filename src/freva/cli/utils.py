"""Collection of utilities of the freva command line argument parser."""

import argparse
from copy import copy
from getpass import getuser
import logging
from typing import Any, Dict, List, Optional
import sys

from evaluation_system.misc import config, logger
from evaluation_system.misc.exceptions import CommandError, hide_exception


def is_admin(raise_error: bool = False) -> bool:
    """Check if the user at runtime is one of the admins.

    Parameters:
    -----------
    raise_error:
        Raise a RuntimeError if user is not admin
    """
    config.reloadConfiguration()
    admin = config.get("admins", [])
    user = getuser()
    if isinstance(admin, str):
        admin = [admin]
    is_admin = user in admin
    if not is_admin and raise_error:
        raise RuntimeError(f"{user} is not in admin list")
    return is_admin


class BaseParser:
    """Base class for common command line argument parsers."""

    admin_commands = ["solr", "check", "doc"]

    def __init__(
        self, sub_commands: List[str], parser: argparse.ArgumentParser
    ) -> None:
        """Create the sub-command parsers."""

        self.parser = parser
        self.subparsers = parser.add_subparsers(help="Available sub-commands:")
        self.sub_commands = sub_commands
        for command in sub_commands:
            getattr(self, f"parse_{command.replace('-','_')}")()

    @property
    def logger(self) -> logging.Logger:
        """Use evaluation_system logger in all classes using ths class."""
        return logger

    def set_debug(self, debug: bool) -> None:
        """Set the logger level to DEBUG."""
        if debug is True:
            self.logger.setLevel(logging.DEBUG)

    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse the command line arguments."""
        args = self.parser.parse_args(argv or None)
        self.kwargs = {k: v for (k, v) in args._get_kwargs() if k != "apply_func"}
        self.set_debug(self.kwargs.pop("debug", False))
        return args

    @classmethod
    def get_subcommands(cls) -> List[str]:
        """Create the available sub commands for a user."""
        sub_commands = [
            "databrowser",
            "plugin",
            "history",
            "crawl-my-data",
            "esgf",
        ]
        if is_admin():
            sub_commands += cls.admin_commands
        return sub_commands

    def _usage(self, *args: Optional[Any], **kwargs: Optional[Any]) -> None:
        """Exit with usage message."""
        self.parser.error(
            "the following sub-commands are "
            f"required: {', '.join(self.sub_commands)}"
        )


class BaseCompleter:
    """Base class for command line argument completers."""

    def __init__(self, metavar: str, choices: Optional[List[str]] = None):
        self.metavar = metavar
        self.choices = choices

    @staticmethod
    def arg_to_dict(args: List[str], append: bool = False) -> Dict[str, List[str]]:
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
        out_dict: Dict[str, List[str]] = {}
        for arg in args:
            try:
                key, value = arg.split("=")
            except ValueError:
                with hide_exception():
                    raise CommandError(f"Bad Option: {arg}")
            if append and key in out_dict:
                out_dict[key].append(value)
            else:
                out_dict[key] = [value]
        return out_dict

    def _to_dict(self, parsed_args: argparse.ArgumentParser) -> Dict[str, List[str]]:
        args = getattr(parsed_args, self.metavar)
        return self.arg_to_dict(args)

    def __call__(self, **kwargs: Optional[str]) -> Optional[List[str]]:
        return self.choices

    @staticmethod
    def _get_choices_from_parser(parser: argparse.ArgumentParser) -> List[str]:

        choices = []
        for action in parser._actions:
            if action.option_strings:
                choice = action.option_strings[0]
            else:
                choice = action.dest
            if choice not in ("facet", "facets", "tool-name", "options"):
                choices.append(choice)
        return choices

    @classmethod
    def get_args_of_subcommand(cls, argv: List[str]) -> List[str]:
        """Get all possible arguments from a freva sub-command."""
        sub_command = argv.pop(0)
        sub_mod = sub_command.replace("-", "_")
        try:
            mod = __import__(f"freva.cli.{sub_mod}", fromlist=[""])
            CliParser = getattr(mod, mod.CLI)()
            return cls._get_choices_from_parser(CliParser.parser)
        except ImportError:
            mod = __import__(f"freva.cli.admin.{sub_command}", fromlist=[""])
        # Admin parsers are sub command parsers and need a parent parser
        parent_parser = argparse.ArgumentParser()
        CliParser = getattr(mod, mod.CLI)(parent_parser)
        sub_cmds = CliParser.sub_commands
        if not argv:
            # Only the 1st admin sub command was given:
            return sub_cmds
        # Get the choices for the 2nd sub command
        next_cmd = argv.pop(0).replace('-', '_')
        try:
            NewParser = getattr(CliParser, f"parse_{next_cmd}")()
        except AttributeError:
            return []
        return cls._get_choices_from_parser(NewParser.parser)

    @classmethod
    def parse_choices(cls, argv: List[str] = sys.argv[1:]):
        """Create the completion choices from given cmd arguments."""
        main_choices = BaseParser.get_subcommands()
        if not argv:
            return cls("", main_choices)
        sub_cmd = argv[0]
        choices = []
        if argv[0] in main_choices:
            choices = cls.get_args_of_subcommand(copy(argv))
        choices = [choice for choice in choices if choice not in argv]
        return cls(sub_cmd, choices)
