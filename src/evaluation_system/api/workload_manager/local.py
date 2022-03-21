from __future__ import annotations
import logging
import os
from pathlib import Path
import subprocess

from .core import Job

logger = logging.getLogger(__name__)


class LocalJob(Job):
    __doc__ = """ Use Jobqueue with local bash commands

    This is mostly for testing.  It uses all the same machinery of
    jobqueue, but rather than submitting jobs to some external job
    queueing system, it launches them locally.

    Parameters
    ----------
    plugin args
    """

    config_name = "local"
    cancel_command = "kill -9"

    def __init__(
        self,
        name=None,
        queue=None,
        project=None,
        resource_spec=None,
        walltime="",
        job_extra=[],
        env_extra=[],
        **kwargs,
    ):
        # Instantiate args and parameters from parent abstract class
        env_extra = ["PID=$(pgrep -f $0)", "sleep 3"] + env_extra
        kwargs["memory"] = 1
        super().__init__(
            name=name, shebang="#!/usr/bin/env bash", env_extra=env_extra, **kwargs
        )

        # Declare class attribute that shall be overridden
        self.job_header = ""
        if self.log_directory:
            out_file = Path(self.log_directory) / f"{self.job_name}-$PID.out"
            self._command_template += f" &> {out_file}"
        logger.debug("Job script: \n %s" % self.job_script())

    def _submit_job(self, script_filename):
        # Should we make this async friendly?
        cmd = ["/usr/bin/env", "bash", script_filename]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return str(process.pid)

    @classmethod
    def _close_job(self, job_id, cancel_command):
        os.kill(int(job_id), 9)
        # from distributed.utils_test import terminate_process
        # terminate_process(self.process)
