import unittest
import os
import logging
import distutils.spawn as spawn

from subprocess import run, PIPE
from time import sleep



def testStartSlurm():
    from evaluation_system.model import slurm, user
    from evaluation_system.misc import config, utils
    """
    This executes a simple slurm scheduler test
    1. check if slurm is available
    2. write a slurm file
    3. execute the file with slurm
    """
    sbatch_exe = spawn.find_executable('sbatch')
    squeue_exe = spawn.find_executable('squeue')
    # check weather the commands exist     
    assert not (sbatch_exe is None), "can not find 'sbatch'"
    assert not (squeue_exe is None), "can not find 'squeue'"
    # create a user object
    test_user = user.User()
    # we need a user to access the std slurm input and output directory         
    slurm_in_dir = os.path.join(test_user.getUserSchedulerInputDir(),
                                test_user.getName())
    # create the slurm file object
    infile = os.path.join(slurm_in_dir, 'slurm_test_input_file')
    # set the SLURM output directory
    slurm_out_dir = test_user.getUserSchedulerOutputDir()
    with open(infile, 'w') as fp:
        sf = slurm.slurm_file()
        sf.set_default_options(test_user,
                               'cat $0',
                               outdir=slurm_out_dir)
        sf.write_to_file(fp)
        fp.flush()

    # create the batch command
    # config.SCHEDULER_COMMAND,
    user = test_user.getName()
    command = ['/bin/bash',
               '-c',
               f'{sbatch_exe} {config.SCHEDULER_OPTIONS} {infile}\n']
    # submit the job 
    p = run(command, stdout=PIPE, stderr=PIPE)
    (stdout, stderr) = p.stdout.decode(), p.stderr.decode()
    logging.debug("scheduler call output:\n" + stdout)
    logging.debug("scheduler call error:\n" + stderr)
    # get the very first line only
    out_first_line = stdout.split('\n')[0]
    # read the id from stdout
    assert out_first_line.split(' ')[0] == 'Submitted', 'Received: ' + str(out_first_line)
    slurm_id = int(out_first_line.split(' ')[-1])
    # now, we check whether the job has been submitted or finished
    sleep(1)
    # create the batch command
    command = ['/bin/bash',
               '-c',
               'squeue -j %i\n' % slurm_id]
    #  we check squeue maybe the job is pending
    p = run(command, stdout=PIPE, stderr=PIPE)
    (stdout, stderr) = p.stdout.decode(), p.stderr.decode()
    # Cancel the job
    p = run(['/bin/bash', '-c', 'scancel', f'{slurm_id}'], stdout=PIPE)
    assert len(p.stdout.decode()) == 0


