"""Module to print command argument line argument choices."""

import sys
from .utils import BaseCompleter


def main() -> None:
    argv = sys.argv[1:]
    comp = BaseCompleter.parse_choices(argv)
    if not comp.choices:
        return
    comp.formated_print()


main()
