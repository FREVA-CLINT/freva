"""Run job in the background on the same system."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import ClassVar, Optional

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

    config_name: ClassVar[str] = "local"
    cancel_command: ClassVar[str] = "kill -QUIT"

    def __init__(
        self,
        name: Optional[str] = None,
        queue: Optional[str] = None,
        project: Optional[str] = None,
        resource_spec: Optional[str] = None,
        walltime: str = "",
        job_extra: Optional[list[str]] = None,
        env_extra: Optional[list[str]] = None,
        **kwargs,
    ):
        # Instantiate args and parameters from parent abstract class
        env_extra = env_extra or []
        env_extra = [
            "cleanup() {",
            "      echo 'Caught SIGINT, cleaning up...'",
            "      kill -QUIT $PLUGIN_ID",
            "      exit 1",
            "}",
            "trap 'cleanup' QUIT",
            "PID=$(pgrep -f $0)",
        ] + env_extra
        kwargs["memory"] = 1
        super().__init__(
            name=name,
            shebang="#!/usr/bin/env bash",
            env_extra=env_extra,
            **kwargs,
        )

        # Declare class attribute that shall be overridden
        self.job_header = ""
        if self.log_directory:
            out_file = Path(self.log_directory) / f"{self.job_name}-$PID.out"
            self._command_template += f" &> {out_file} &\n"
        self._command_template += "PLUGIN_ID=$!\nwait $PLUGIN_ID"
        logger.debug(f"Job script: \n {self.job_script()}")

    def _submit_job(self, script_filename):
        # Should we make this async friendly?
        cmd = ["/usr/bin/env", "bash", script_filename]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            env=os.environ.copy(),
        )
        return str(process.pid)

    @classmethod
    def _close_job(cls, job_id, cancel_command):
        os.kill(int(job_id), 9)
