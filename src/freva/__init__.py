import logging
import os
import warnings

from evaluation_system import __version__
from evaluation_system.misc import logger

from ._databrowser import count_values, databrowser, facet_search
from ._esgf import esgf_browser, esgf_facets, esgf_datasets, esgf_download, esgf_query
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
from .utils import PluginStatus, config, copy_doc_from, is_jupyter

warnings.filterwarnings("always", category=DeprecationWarning, module="freva.*")

if is_jupyter():
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    logger.setLevel(logging.WARNING)


@copy_doc_from(UserData.add)
def add_user_data(
    product: str,
    *paths: os.PathLike,
    how: str = "copy",
    override: bool = False,
    **defaults: str,
) -> None:
    return UserData().add(product, *paths, how=how, override=override, **defaults)


@copy_doc_from(UserData.index)
def index_user_data(
    *crawl_dirs: os.PathLike,
    dtype: str = "fs",
    continue_on_errors: bool = False,
    **kwargs: bool,
) -> None:
    return UserData().index(
        *crawl_dirs,
        dtype=dtype,
        continue_on_errors=continue_on_errors,
        **kwargs,
    )


@copy_doc_from(UserData.delete)
def delete_user_data(*paths: os.PathLike, delete_from_fs: bool = False) -> None:
    return UserData().delete(*paths, delete_from_fs=delete_from_fs)


@copy_doc_from(PluginStatus)
def get_plugin_status(history_id: int) -> "PluginStatus":
    return PluginStatus(history_id)


__all__ = [
    "__version__",
    "add_user_data",
    "config",
    "count_values",
    "databrowser",
    "delete_user_data",
    "esgf_browser",
    "esgf_facets",
    "esgf_datasets",
    "esgf_download",
    "esgf_query",
    "facet_search",
    "get_plugin_status",
    "history",
    "index_user_data",
    "list_plugins",
    "plugin_doc",
    "plugin_info",
    "plugin_doc",
    "PluginStatus",
    "UserData",
]
