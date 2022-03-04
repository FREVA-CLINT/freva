"""Module to print command argument line argument choices."""

import sys
import logging
from .utils import print_choices, logger

logger.setLevel(logging.ERROR)

try:
    print_choices(sys.argv[1:])
except KeyboardInterrupt:
    pass
