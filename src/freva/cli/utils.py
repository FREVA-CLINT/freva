"""Collection of utilities of the freva command line argument parser."""

import argparse
import logging
from typing import Dict, List, Optional
from evaluation_system.misc import logger


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
    def arg_to_dict(args: str) -> Dict[str, str]:
        """Convert a parsed argument to a dictionary."""
        return dict(arg.split('=') for arg in args)

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

    def parse_args(self, args: List[str] = None) -> argparse.Namespace:
        """Parse the command line arguments."""
        args = self.parser.parse_args(args)
        self.kwargs = {k: v for (k, v) in args._get_kwargs() if k != 'apply_func'}
        self.set_debug(self.kwargs.pop('debug', False))
        return args
