import logging
import os
import warnings

from evaluation_system import __version__
from evaluation_system.misc import logger

from ._databrowser import count_values, databrowser, facet_search
from ._esgf import esgf
from ._history import history
from ._plugin import (
    get_tools_list,
    list_plugins,
    plugin_doc,
    plugin_info,
    read_plugin_cache,
    run_plugin,
)
from ._user_data import UserData
from .utils import PluginStatus, config, is_jupyter

warnings.filterwarnings("always", category=DeprecationWarning, module="freva.*")

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
    "plugin_info",
    "plugin_doc",
    "esgf",
    "history",
    "PluginStatus",
]
