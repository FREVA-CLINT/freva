"""Definitions of custom exections and warnings."""

from contextlib import contextmanager
import logging
import sys
import warnings

from evaluation_system.misc import logger


def deprication_warning(old_method: str, new_method: str, klass: str) -> None:
    """Show a deprication warning for a depricated module."""
    msg = (
        f"The method `{old_method}` of `{klass}` is depricated, "
        "and will be subject to removel in future releases, please "
        f"instruct your code to call the `{new_method}` method instead."
    )
    if logger.level <= logging.DEBUG:
        raise AttributeError(
            f"{klass} as no attribute: {old_method}, use {new_method} instead"
        )
    warnings.warn(msg, category=DeprecationWarning)
    logger.warning(msg)


class ConfigurationException(Exception):
    """Mark exceptions thrown in this package"""


class PluginNotFoundError(Exception):
    """Exeption Definition for missing Plugins."""


class ValidationError(Exception):
    """Thrown if some variable contains an improper value."""


class ParameterNotFoundError(Exception):
    """Thrown if some parameter is not in the database."""


class CommandError(Exception):
    """
    Generic exception to raise and log different fatal errors.
    """

    def __init__(self, msg):
        super(CommandError).__init__(type(self))
        self.msg = f"{msg}\nUse --help for getting help"

    def __str__(self):
        return self.msg


class PluginManagerException(Exception):
    """For all problems generating while using the plugin manager."""


@contextmanager
def hide_exception():
    """
    Suppress traceback, only print the exception type and value
    """
    default_value = getattr(sys, "tracebacklimit", 1000)
    sys.tracebacklimit = 0
    yield
    sys.tracebacklimit = default_value  # revert changes
