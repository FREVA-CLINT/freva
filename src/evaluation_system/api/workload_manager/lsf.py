"""Submit jobs to the lsf workload manager."""
from __future__ import annotations
from distutils.version import LooseVersion

import logging
import math
import os
from pathlib import Path
import re
import subprocess
import toolz
from typing import Any, cast, ClassVar, Optional, Coroutine, Union

from .core import Job

logger = logging.getLogger(__name__)


class LSFJob(Job):
    submit_command: ClassVar[str] = "bsub"
    cancel_command: ClassVar[str] = "bkill"
    config_name: ClassVar[str] = "lsf"

    def __init__(
        self,
        scheduler: Optional[str] = None,
        name: Optional[str] = None,
        queue: Optional[str] = None,
        project: Optional[str] = None,
        ncpus: Optional[int] = None,
        mem: Optional[int] = None,
        walltime: str = "",
        job_extra: Optional[list[str]] = None,
        lsf_units: Optional[str] = None,
        use_stdin: bool = False,
        **base_class_kwargs,
    ):
        super().__init__(scheduler=scheduler, name=name, **base_class_kwargs)

        self.use_stdin = use_stdin
        header_lines = []
        job_extra = job_extra or []
        # LSF header build
        if self.name is not None:
            header_lines.append("#BSUB -J %s" % self.job_name)
        if self.log_directory is not None:
            header_lines.append(
                "#BSUB -o %s/%s-%%J.out" % (self.log_directory, self.name or "worker")
            )
        if queue is not None:
            header_lines.append("#BSUB -q %s" % queue)
        if project is not None:
            header_lines.append('#BSUB -P "%s"' % project)
        if ncpus is None:
            # Compute default cores specifications
            ncpus = self.worker_cores
            logger.info(
                "ncpus specification for LSF not set, initializing it to %s" % ncpus
            )
        if ncpus is not None:
            header_lines.append("#BSUB -n %s" % ncpus)
            if ncpus > 1:
                # span[hosts=1] _might_ affect queue waiting
                # time, and is not required if ncpus==1
                header_lines.append('#BSUB -R "span[hosts=1]"')
        if mem is None:
            # Compute default memory specifications
            mem = cast(int, self.worker_memory)
            logger.info(
                "mem specification for LSF not set, initializing it to %s bytes" % mem
            )
        if mem is not None:
            lsf_units = lsf_units if lsf_units is not None else lsf_detect_units()
            memory_string = lsf_format_bytes_ceil(mem, lsf_units=lsf_units)
            header_lines.append("#BSUB -M %s" % memory_string)
        if walltime is not None:
            header_lines.append("#BSUB -W %s" % walltime)
        header_lines.extend(["#BSUB %s" % arg for arg in job_extra])

        # Declare class attribute that shall be overridden
        self.job_header = "\n".join(header_lines)

        logger.debug("Job script: \n %s" % self.job_script())

    def _submit_job(self, script_filename: Union[Path, str]) -> str:
        script_filename = str(script_filename)
        if self.use_stdin:
            piped_cmd = [self.submit_command + "< " + script_filename + " 2> /dev/null"]
            return self._call(piped_cmd, shell=True)
        else:
            return super()._submit_job(script_filename)


def lsf_format_bytes_ceil(n: int, lsf_units: str = "mb") -> str:
    """Format bytes as text

    Convert bytes to megabytes which LSF requires.

    Parameters
    ----------
    n: int
        Bytes
    lsf_units: str
        Units for the memory in 2 character shorthand, kb through eb

    Examples
    --------
    >>> lsf_format_bytes_ceil(1234567890)
    '1235'
    """
    lsf_units = lsf_units.lower()[0]
    converter = {"k": 1, "m": 2, "g": 3, "t": 4, "p": 5, "e": 6, "z": 7}
    return "%d" % math.ceil(n / (1000 ** converter[lsf_units]))


def lsf_detect_units() -> str:
    """Try to autodetect the unit scaling on an LSF system"""
    # Search for automatically, Using docs from LSF 9.1.3 for search/defaults
    unit = "kb"  # Default fallback unit
    try:
        # Start looking for the LSF conf file
        conf_dir = "/etc"  # Fall back directory
        # Search the two environment variables the docs say it could be at
        # (likely a typo in docs)
        for conf_env in ["LSF_ENVDIR", "LSF_CONFDIR"]:
            conf_search = os.environ.get(conf_env, None)
            if conf_search is not None:
                conf_dir = conf_search
                break
        conf_path = os.path.join(conf_dir, "lsf.conf")
        conf_file = open(conf_path, "r").readlines()
        # Reverse order search
        # (in case defined twice, get the one which will actually be processed)
        for line in conf_file[::-1]:
            # Look for very specific line
            line = line.strip()
            if not line.strip().startswith("LSF_UNIT_FOR_LIMITS"):
                continue
            # Found the line, infer the unit, only first 2 chars after "="
            unit = line.split("=")[1].lower()[0]
            break
        logger.debug(
            "Setting units to %s from the LSF config file at %s" % (unit, conf_file)
        )
    # Trap the lsf.conf does not exist, and the conf
    # file not setup right (i.e. "$VAR=xxx^" regex-form)
    except (EnvironmentError, IndexError):
        logger.debug(
            "Could not find LSF config or config file did not have "
            "LSF_UNIT_FOR_LIMITS set. Falling back to "
            "default unit of %s." % unit
        )
    return unit


@toolz.memoize
def lsf_version() -> Optional[LooseVersion]:
    out, _ = subprocess.Popen("lsid", stdout=subprocess.PIPE).communicate()
    versn: str = out.decode()
    match = re.search(r"(\d+\.)+\d+", versn)
    if match is not None:
        return LooseVersion(match.group())
    return None
