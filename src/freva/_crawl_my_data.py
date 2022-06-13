"""Update user data in the apache solr data search server."""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Union

from evaluation_system.model.user import User
from evaluation_system.misc import config
from evaluation_system.misc.exceptions import ValidationError, ConfigurationException
from evaluation_system.model.solr_core import SolrCore
from evaluation_system.api.user_data import DataReader

__all__ = ["crawl_my_data"]


def _validate_user_dirs(*crawl_dirs: Optional[Union[str, Path]]) -> tuple[Path, ...]:

    root_path = DataReader.get_output_directory()
    user_root_path = root_path / f"user-{User().getName()}"
    user_paths: tuple[Path, ...] = ()
    for crawl_dir in crawl_dirs or (user_root_path,):
        crawl_dir = Path(crawl_dir or user_root_path).expanduser().absolute()
        try:
            _ = crawl_dir.relative_to(root_path)
        except ValueError as error:
            raise ValidationError(
                f"You are only allowed to crawl data in {root_path}"
            ) from error
        user_paths += (crawl_dir,)
    return user_paths


def crawl_my_data(*crawl_dirs: Optional[Union[str, Path]], dtype: str = "fs") -> None:
    """Crawl user output data to reingest it into the solr server.

    The data needs to be of a certain strucutre.

    Parameters
    ----------
    crawl_dirs:
        The data path(s) that needs to be crawled
    dtype:
        The data type, currently only files on the file system are supported.

    Raises
    ------
    ValidationError:
        If crawl_dirs do not belong to current user.

    Example
    -------

    .. execute_code::

        import freva
        freva.crawl_my_data()

    """
    if dtype not in ("fs",):
        raise NotImplementedError("Only data on POSIX file system is supported")
    print("Status: crawling ...", end="")
    for crawl_dir in _validate_user_dirs(*crawl_dirs):
        SolrCore.load_fs(
            crawl_dir, chunk_size=200, abort_on_errors=True, drs_type="crawl_my_data"
        )
    print("ok", flush=True)
