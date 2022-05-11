"""Module to encapsulates the access to repositories."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Union, Iterator

from git import Repo
from evaluation_system.misc import logger

__version_cache: dict[str, tuple[str, str]] = {}


@contextmanager
def set_repo_safe(dir_name: Union[str, Path]) -> Iterator[Repo]:
    """Context manager that sets a given repository dir as temporarly safe.

    Parameters
    ----------
    dir_name: Union[str, Path]
        Path to the repository dir that is set to be safe

    Returns
    -------
    Iterator[git.Repo]:
        Instance of the gitpython Repo class
    """
    repo = Repo(dir_name, search_parent_directories=True)
    with repo.config_reader("global") as config_r:
        safe_dirs = {}
        if config_r.has_section("safe"):
            safe_dirs = dict(config_r.items_all("safe"))
    with repo.config_writer("global") as config_w:
        try:
            config_w.add_value("safe", "directory", str(dir_name)).release()
            yield repo
        except Exception as error:
            raise error
        finally:
            config_w.remove_section("safe")
            for key, values in safe_dirs.items():
                for value in values:
                    config_w.add_value("safe", key, value)


def get_version(src_file: str) -> tuple[str, str]:
    """Acquire git remote repo url and last commit hash.

    Parameters
    ----------
    src_file: str
        Path to the plugin wrapper API file

    Returns
    -------
    tuple[str, str]
        tuple holding remote repo url, last git commit hash

    """
    retval = __version_cache.get(src_file, None)
    if retval is None:
        with set_repo_safe(Path(src_file).parent) as repo:
            try:
                repository = next(repo.remote(name="origin").urls)
                version = repo.head.object.hexsha
            except Exception as error:
                logger.error("Could not read git version")
                logger.error("Error while reading git version:\n%s", str(error))
                repository = "unknown"
                version = "unknown"
        retval = (repository, version)
        __version_cache[str(src_file)] = retval
    return retval
