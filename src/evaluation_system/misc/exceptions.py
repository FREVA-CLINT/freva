"""Definitions of custom exections."""

from contextlib import contextmanager
import sys

class PluginNotFoundError(Exception):
    """Exeption Definition for missing Plugins."""
    pass

class ValidationError(Exception):
    """Thrown if some variable contains an improper value."""
    pass

class ParameterNotFoundError(Exception):
    """Thrown if some parameter is not in the database."""
    pass

class CommandError(Exception):
    """
    Generic exception to raise and log different fatal errors.
    """
    def __init__(self, msg):
        super(CommandError).__init__(type(self))
        self.msg = f"{msg}\nUse --help for getting help"

    def __str__(self):
        return self.msg

@contextmanager
def hide_exception():
    """
    Suppress traceback, only print the exception type and value
    """
    default_value = getattr(sys, "tracebacklimit", 1000)
    sys.tracebacklimit = 0
    yield
    sys.tracebacklimit = default_value  # revert changes



