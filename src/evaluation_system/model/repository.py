"""
..moduleauthor: Oliver Kunst / Sebastian Illing

This module encapsulates the access to repositories.
"""

import os
import logging
from subprocess import Popen, PIPE

from evaluation_system.misc import config

log = logging.getLogger(__name__)

__version_cache = {}


def getVersion(src_file):
   
    retval = __version_cache.get(src_file, None)
    
    if retval is None:
        (dir_name, filename) = os.path.split(src_file)
        command = 'module load git > /dev/null 2> /dev/null;'
        if dir_name:
            command += 'cd %s 2> /dev/null;' % dir_name
        command += 'git config --get remote.origin.url;'
        command += 'git show-ref --heads --hash'
        options = config.get(config.GIT_BASH_STARTOPTIONS, '-lc')
        bash = ['/bin/bash',  options,  command]
        p = Popen(bash, stdout=PIPE, stderr=PIPE)
        
        (stdout, stderr) = p.communicate()
    
        try:
            lines = stdout.split('\n')
            repository = lines[-3]
            version = lines[-2]
        except Exception as e:
            if not stderr:
                stderr = str(e)
               
            log.warning("Could not read git version")
            log.debug("Error while reading git version:\n%s", stderr)
    
            repository = 'unknown'
            version = 'unknown'
            
        retval = (repository, version)
        __version_cache[src_file] = retval

    return retval
