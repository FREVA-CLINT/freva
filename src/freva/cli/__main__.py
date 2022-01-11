"""Module to print command argument line argument choices."""

import sys
from .utils import BaseCompleter


def main() -> None:
    argv = [arg.strip() for arg in sys.argv[1:] if arg.strip()]
    comp = BaseCompleter.parse_choices(argv)
    if not comp.choices:
        return
    comp.formated_print()


main()
