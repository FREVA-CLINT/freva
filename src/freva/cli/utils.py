"""Collection of utilities of the freva command line argument parser."""

import argparse
from getpass import getuser
import logging
from typing import Any, Dict, List, Optional
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


class BaseCompleter:
    """Base class for command line argument completers."""

    def __init__(self, metavar: str, choices: Optional[List[str]] = None):
        self.metavar = metavar
        self.choices = choices

    @staticmethod
    def arg_to_dict(args: str, append: bool = False) -> Dict[str, List[str]]:
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


class BaseParser:
    """Base class for common command line argument parsers."""

    def __init__(self,
                 sub_commands: List[str],
                 parser: argparse.ArgumentParser) -> None:
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

    def _usage(self, *args: Optional[Any], **kwargs: Optional[Any]) -> None:
        """Exit with usage message."""
        self.parser.error(
            "the following sub-commands are "
            f"required: {', '.join(self.sub_commands)}"
        )
