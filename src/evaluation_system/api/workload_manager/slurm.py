from __future__ import annotations
import logging
import math

from .core import Job

logger = logging.getLogger(__name__)


class SLURMJob(Job):
    # Override class variables
    submit_command = "sbatch"
    cancel_command = "scancel"
    config_name = "slurm"

    def __init__(
        self,
        name=None,
        queue=None,
        project=None,
        walltime="",
        job_cpu=None,
        job_mem=None,
        job_extra=[],
        **base_class_kwargs,
    ):
        super().__init__(name=name, **base_class_kwargs)

        header_lines = []
        # SLURM header build
        if self.job_name is not None:
            header_lines.append("#SBATCH -J %s" % self.job_name)
        if self.log_directory is not None:
            header_lines.append(
                "#SBATCH -o %s/%s-%%J.out"
                % (self.log_directory, self.job_name or "worker")
            )
        if queue is not None:
            header_lines.append("#SBATCH -p %s" % queue)
        if project is not None:
            header_lines.append("#SBATCH -A %s" % project)

        # Init resources, always 1 task,
        # and then number of cpu is processes * threads if not set
        header_lines.append("#SBATCH -n 1")
        header_lines.append(
            "#SBATCH --cpus-per-task=%d" % (job_cpu or self.worker_cores)
        )
        # Memory
        memory = job_mem
        if job_mem is None:
            memory = slurm_format_bytes_ceil(self.worker_memory)
        if memory is not None:
            header_lines.append("#SBATCH --mem=%s" % memory)

        if walltime is not None:
            header_lines.append("#SBATCH -t %s" % walltime)
        header_lines.extend(["#SBATCH %s" % arg for arg in job_extra])

        # Declare class attribute that shall be overridden
        self.job_header = "\n".join(header_lines)


def slurm_format_bytes_ceil(n):
    """Format bytes as text.

    SLURM expects KiB, MiB or Gib, but names it KB, MB, GB. SLURM does
    not handle Bytes, only starts at KB.

    >>> slurm_format_bytes_ceil(1)
    '1K'
    >>> slurm_format_bytes_ceil(1234)
    '2K'
    >>> slurm_format_bytes_ceil(12345678)
    '13M'
    >>> slurm_format_bytes_ceil(1234567890)
    '2G'
    >>> slurm_format_bytes_ceil(15000000000)
    '14G'
    """
    if n >= (1024**3):
        return "%dG" % math.ceil(n / (1024**3))
    if n >= (1024**2):
        return "%dM" % math.ceil(n / (1024**2))
    if n >= 1024:
        return "%dK" % math.ceil(n / 1024)
    return "1K" % n
