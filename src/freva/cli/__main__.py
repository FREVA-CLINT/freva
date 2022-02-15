"""Module to print command argument line argument choices."""

import sys
from .utils import print_choices


try:
    print_choices(sys.argv[1:])
except KeyboardInterrupt:
    pass
