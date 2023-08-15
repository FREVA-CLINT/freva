import logging
import os
import warnings

from evaluation_system import __version__
from evaluation_system.misc import logger
from ._user_data import UserData
from ._databrowser import databrowser, count_values, facet_search
from ._plugin import (
    run_plugin,
    list_plugins,
    plugin_doc,
    read_plugin_cache,
    get_tools_list,
)
from ._esgf import esgf
from ._history import history
from .utils import config, is_jupyter

warnings.filterwarnings(
    "always", category=DeprecationWarning, module="freva.*"
)

if is_jupyter():
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    logger.setLevel(logging.WARNING)

__all__ = [
    "__version__",
    "config",
    "UserData",
    "databrowser",
    "count_values",
    "facet_search",
    "run_plugin",
    "list_plugins",
    "plugin_doc",
    "esgf",
    "history",
]
