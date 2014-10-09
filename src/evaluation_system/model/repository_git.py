'''
This module encapsulates the access to repositorys. 
'''

def getVersion(srcFile):
    repository = 'unknown'
    version = 'unknown'

    (dirname, filename) = os.path.split(srcfile)
    command = 'module load git > /dev/null 2> /dev/null;'
    if dirname:
        command += 'cd %s 2> /dev/null;' % dirname
    command += 'git config --get remote.origin.url;'
    command += 'git show-ref --heads --hash'
    bash = ['/bin/bash',  '-lc',  command]
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

    return (repository, version)

