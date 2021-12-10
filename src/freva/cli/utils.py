"""Collection of utilities of the freva command line argument parser."""

import argparse
import logging
from typing import Dict, List, Optional
from evaluation_system.misc import logger
from evaluation_system.misc.exceptions import CommandError, hide_exception

parse_type = argparse._SubParsersAction
"""Argparses supaparser type"""
arg_type = argparse.Namespace
"""Argparses Namespace type (after parsing the cmd arguments)"""

class BaseCompleter:
    """Base class for command line argument completers."""

    def __init__(self,
                 metavar: Optional[str] = None,
                 choices: Optional[str] = None
                 ):
        self.metavar = metavar
        self.choices = choices

    @staticmethod
    def arg_to_dict(args: str, append: bool = False) -> Dict[str, str]:
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
        out_dict = {}
        for arg in args:
            try:
                key, value = arg.split('=')
            except ValueError:
                with hide_exception():
                    raise CommandError(f'Bad Option: {arg}')
            if append and key in out_dict:
                if isinstance(out_dict[key], str):
                    out_dict[key] = [out_dict[key]]
                out_dict[key].append(value)
            else:
                out_dict[key] = value
        return out_dict

    def _to_dict(self, parsed_args: arg_type) -> Dict[str, str]:
        args = getattr(parsed_args, self.metavar)
        return self.arg_to_dict(args)

    def __call__(self, **kwargs: Optional[str]) -> List[str]:
        return self.choices

class BaseParser:

    def set_debug(self, debug: bool):
        """Set the logger level to DEBUG."""
        if debug is True:
            logger.setLevel(logging.DEBUG)

    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse the command line arguments."""
        args = self.parser.parse_args(argv)
        self.kwargs = {k: v for (k, v) in args._get_kwargs() if k != 'apply_func'}
        self.set_debug(self.kwargs.pop('debug', False))
        return args
