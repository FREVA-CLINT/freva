from evaluation_system import __version__
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
import warnings

warnings.filterwarnings("always", category=DeprecationWarning, module="freva.*")


__all__ = [
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
