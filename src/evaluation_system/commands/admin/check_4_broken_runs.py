#!/usr/bin/env python

"""
check_4_broken_runs -- Checks DB and slurm for broken runs and updates history status

@copyright:  2016 FU Berlin. All rights reserved.

@contact:    sebastian.illing@met.fu-berlin.de
"""

from evaluation_system.commands import FrevaBaseCommand, CommandError
from evaluation_system.model.history.models import History


class Command(FrevaBaseCommand):
    _args = [
        {'name': '--debug', 'short': '-d',
         'help': 'turn on debugging info and show stack trace on exceptions.', 'action': 'store_true'},
        {'name': '--help', 'short': '-h',
         'help': 'show this help message and exit', 'action': 'store_true'},
    ]

    __short_description__ = '''Check for broken runs in SLURM'''

    def _run(self):
        # get all jobs with status "running" and started with scheduler
        import datetime
        
        running_jobs = History.objects.filter(status=History.processStatus.running).exclude(slurm_output=0)
        for job in running_jobs:
            slurm_status = job.get_slurm_status()
            if 'cancelled' in slurm_status.lower() or 'timeout' in slurm_status.lower() or 'fail' in slurm_status.lower():
                print slurm_status, job.tool
                print 'Setting job %s to broken' % job.id
                job.status = job.processStatus.broken
                job.save()
            elif 'completed' in slurm_status.lower():
                job.status = job.processStatus.finished
                job.save()

if __name__ == "__main__":  # pragma: nocover
    Command().run()
