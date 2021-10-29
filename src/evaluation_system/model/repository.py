"""
..moduleauthor: Oliver Kunst / Sebastian Illing

This module encapsulates the access to repositories.
"""

import os
import logging
from git import Repo
from evaluation_system.misc import config

log = logging.getLogger(__name__)

__version_cache = {}


def getVersion(src_file):
   
    retval = __version_cache.get(src_file, None)
    if retval is None:
        (dir_name, filename) = os.path.split(src_file)
        try:
            
            repo = Repo(dir_name, search_parent_directories=True)
            repository = next(repo.remote(name='origin').urls)
            version = repo.head.object.hexsha
       
        except Exception as e:
            log.warning("Could not read git version")
            log.info("Error while reading git version:\n%s", str(e))
            repository = 'unknown'
            version = 'unknown'
            
        retval = (repository, version)
        __version_cache[src_file] = retval

    return retval
