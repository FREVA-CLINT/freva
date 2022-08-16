"""Module to print command argument line argument choices."""

import sys
import logging

import lazy_import
from evaluation_system.misc import logger

print_choices = lazy_import.lazy_function("freva.cli.utils.print_choices")


logger.setLevel(logging.ERROR)

try:
    print_choices(sys.argv[1:])
except KeyboardInterrupt:
    pass
