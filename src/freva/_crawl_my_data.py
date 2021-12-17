"""Crawl user data and ingest metadata into the solr server."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Tuple

from evaluation_system.model.user import User
from evaluation_system.misc import config
from evaluation_system.misc.exceptions import ValidationError, ConfigurationException
from evaluation_system.model.solr_core import SolrCore

__all__ = ["crawl_my_data"]


def _validate_user_dirs(*crawl_dirs: Optional[Union[str, Path]]) -> Tuple[Path]:
    try:
        root_path = Path(config.get("project_data")).absolute()
    except ConfigurationException:
        config.reloadConfiguration()
        root_path = Path(config.get("project_data")).absolute()
    user_root_path = root_path / f"user-{User().getName()}"
    user_paths = ()
    for crawl_dir in crawl_dirs or (user_root_path,):
        crawl_dir = Path(crawl_dir or user_root_path).expanduser().absolute()
        if not crawl_dir.is_relative_to(root_path):
            raise ValidationError(f"You are only allowed to crawl data in {root_path}")
        user_paths += (crawl_dir,)
    return user_paths


def crawl_my_data(*crawl_dirs: Optional[Union[str, Path]], dtype: str = "fs") -> None:
    """Crawl user output data to reingest it into the solr server.

    The data needs to be of a certain strucutre. Please follow the following
    instructions: <URL HERE> on how to be able to ingest your data.

    Parameters:
    -----------
    crawl_dirs:
        The data path(s) that needs to be crawled
    dtype:
        The data type currently only files on the file system are supported.
    """
    if dtype not in ("fs",):
        raise NotImplementedError("Only data on POSIX file system is supported")
    print(f"Status: crawling ...", end="")
    for crawl_dir in _validate_user_dirs(*crawl_dirs):
        SolrCore.load_fs(
            crawl_dir, chunk_size=200, abort_on_errors=True, drs_type="crawl_my_data"
        )
    print("ok", flush=True)
