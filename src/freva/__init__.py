from evaluation_system import __version__
from ._crawl_my_data import index_my_data, add_my_data, delete_my_data
from ._databrowser import databrowser
from ._plugin import (
    run_plugin,
    list_plugins,
    plugin_doc,
    read_plugin_cache,
    get_tools_list,
)
from ._esgf import esgf
from ._history import history

__all__ = [
    "index_my_data",
    "add_my_data",
    "delete_my_data",
    "databrowser",
    "run_plugin",
    "list_plugins",
    "plugin_doc",
    "esgf",
    "history",
]
