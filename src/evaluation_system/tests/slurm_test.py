import unittest
import os
import logging
import distutils.spawn as spawn

from subprocess import Popen, PIPE, STDOUT
from time import sleep

from evaluation_system.model import slurm, user
from evaluation_system.misc import config, utils

class Test(unittest.TestCase):
        
    def testStartSlurm(self):
        """
        This executes a simple slurm scheduler test
        1. check if slurm is available
        2. write a slurm file
        3. execute the file with slurm
        """
        sbatch_exe = spawn.find_executable('sbatch')
        squeue_exe = spawn.find_executable('squeue')
        
        # check weather the commands exist     
        self.assertFalse(sbatch_exe is None, "can not find 'sbatch'")
        self.assertFalse(squeue_exe is None, "can not find 'squeue'")
        
        # create a user object
        testuser = user.User()
        
        # we need a user to access the std slurm input and output directory         
        slurmindir = os.path.join(testuser.getUserSchedulerInputDir(),
                                  testuser.getName())
        
        if not os.path.exists(slurmindir):
            utils.supermakedirs(slurmindir, 0777)
            
        # create the slurm file object
        infile = os.path.join(slurmindir, 'slurm_test_input_file')

        # set the SLURM output directory
        slurmoutdir = testuser.getUserSchedulerOutputDir()

        if not os.path.exists(slurmoutdir):
            utils.supermakedirs(slurmoutdir, 0777)

        with open(infile, 'w') as fp:
            sf = slurm.slurm_file()
        
            sf.set_default_options(self._user,
                                   'cat $0',
                                   outdir=self._slurmoutdir)
        
            sf.write_to_file(fp)
            fp.flush()

        
        # create the batch command
        command = ['/bin/bash',
                   '-c',
                   '%s %s --uid=%s %s\n' % (config.SCHEDULER_COMMAND,
                                            config.SCHEDULER_OPTIONS,
                                            self._user.getName(),
                                            self._infile)
          ]

        # submit the job 
        p = Popen(command, stdout=PIPE, stderr=STDOUT)
        (stdout, stderr) = p.communicate()

        logging.debug("scheduler call output:\n" + str(stdout))
        logging.debug("scheduler call error:\n" + str(stderr))
        
        # get the very first line only
        out_first_line = stdout.split('\n')[0]
                
        # read the id from stdout
        self.assertTrue(out_first_line.split(' ')[0] == 'Submitted')
        slurm_id = int(out_first_line.split(' ')[-1])
                 
        
        # now, we check whether the job has been submitted or finished
        sleep(1)

        # create the batch command
        command = ['/bin/bash',
                   '-c',
                   'squeue -j %i\n' % slurm_id
          ]

        #  we check sqeue maybe the job is pending
        p = Popen(command, stdout=PIPE, stderr=STDOUT)
        (stdout, stderr) = p.communicate()
        
        if not len(stdout.split('\n')) > 1:
            slurmoutfile = os.path.join(slurmoutdir, 'slurm-%i.out' % slurm_id)
            self.assertTrue(os.path.isfile(slurmoutfile))
        