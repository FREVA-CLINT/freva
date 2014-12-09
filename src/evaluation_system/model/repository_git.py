'''
This module encapsulates the access to repositorys. 
'''

import os
import logging
from subprocess import Popen, PIPE

from evaluation_system.misc import config

log = logging.getLogger(__name__)

__version_cache = {}

def getVersion(srcfile):
    repository = 'unknown'
    version = 'unknown'
    
    retval = __version_cache.get(srcfile, None)
    
    if retval is None:
        (dirname, filename) = os.path.split(srcfile)
        command = 'module load git > /dev/null 2> /dev/null;'
        if dirname:
            command += 'cd %s 2> /dev/null;' % dirname
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
        except Exception, e:
            if not stderr:
                stderr = str(e)
               
            log.warn("Could not read git version")
            log.debug("Error while reading git version:\n%s", stderr)
    
            repository = 'unknown'
            version = 'unknown'
            
        retval = (repository, version)
        __version_cache[srcfile] = retval

    return retval

