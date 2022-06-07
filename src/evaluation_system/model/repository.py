"""Module to encapsulates the access to repositories."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import os
from typing import Iterator

import git
from evaluation_system.misc import logger

__version_cache: dict[str, tuple[str, str]] = {}


@contextmanager
def set_repo_safe(dir_name: os.PathLike) -> Iterator[git.Repo]:
    """Context manager that sets a given repository dir as temporarly safe.

    This needs to be done to not make git complain about the fact that the
    repositories directory doesn't belong to the person who is trying to
    retrieve the repository information. Before we instruct git to read the
    repo we tell it that his directory is save by temporarly adding a safe
    flag to the global git settings. After the repo has been processed by git
    this safe flag is removed again. This is probaply not the best way of
    dealing with this issue. Still, for example setting repositories to as
    shared did not solve the issue.

    Parameters
    ----------
    dir_name: os.PathLike
        Path to the repository dir that is set to be safe

    Returns
    -------
    Iterator[git.Repo]:
        Instance of the gitpython Repo class
    """
    repo = git.Repo(dir_name, search_parent_directories=True)

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
        try:
            with set_repo_safe(Path(src_file).parent) as repo:
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
