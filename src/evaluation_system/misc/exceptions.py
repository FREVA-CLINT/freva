"""Definitions of custom exceptions and warnings."""

import logging
import sys
import warnings
from contextlib import contextmanager
from typing import Any, Callable

from evaluation_system.misc import logger


def deprecated_method(klass: str, new_method: str):
    """Show a deprecation warning for a deprecated method."""

    def call_deprecated_method(function: Callable[[Any], Any]) -> Callable[[Any], Any]:
        def inner(*args: Any, **kwargs: Any) -> Any:
            if logger.level <= logging.DEBUG:
                raise AttributeError(
                    f"{klass} as no attribute: {function.__name__}, use "
                    f"{new_method} instead"
                )
            msg = (
                f"The `{function.__name__}` of {klass} is deprecated and "
                "might be subject to removal in the future. Please consider "
                f"renaming the `{klass}.{function.__name__}` method to "
                f"`{klass}.{new_method}`"
            )
            logger.warning(msg)
            return function(*args, **kwargs)

        return inner

    return call_deprecated_method


class ConfigurationException(Exception):
    """Mark exceptions thrown in this package"""


class PluginNotFoundError(Exception):
    """Exception definition for missing Plugins."""


class ValidationError(Exception):
    """Thrown if some variable contains an improper value."""


class ParameterNotFoundError(Exception):
    """Thrown if some parameter is not in the database."""


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
