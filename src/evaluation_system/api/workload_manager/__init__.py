"""Collection of methods and classes for submitting plugins to a workload manager."""
from pathlib import Path
from typing import Optional

from .core import Job

from .local import LocalJob
from .lsf import LSFJob
from .moab import MoabJob
from .oar import OARJob
from .pbs import PBSJob
from .sge import SGEJob
from .slurm import SLURMJob


def _get_job_object(system: str) -> Job:
    """Get the correct job scheduler object for a given workload manager."""
    job_objects = dict(
        local=LocalJob,
        lfs=LSFJob,
        moab=MoabJob,
        oar=OARJob,
        pbs=PBSJob,
        sge=SGEJob,
        slurm=SLURMJob,
    )
    try:
        return job_objects[system]
    except KeyError:
        raise NotImplementedError(
            f"{system} scheduler not implemented, "
            f"choose from {' '.join(job_objects.keys())}"
        )


def cancel_command(system: str, job_id: int) -> str:
    """Construct a cancel command.

    Parameters:
    ===========

    system:
        Name of the workload manager system (slurm, pbs, moab, etc)
    job_id:
        The job id that is canceled
    """
    job_object = _get_job_object(system)
    return f"{job_object.cancel_command} {job_id}"


def schedule_job(
    system: str,
    source: Path,
    config: dict[str, str],
    log_directory: Optional[str] = None,
    delete_job_script: bool = True,
) -> tuple[int, str]:
    """Create a scheduler object from a given scheduler configuration.

    Parameters:
    ===========
    system:
        Name of the workload manager system (slurm, pbs, moab, etc)
    source:
        Path the to source script that activates freva
    config:
        Configuration to setup a job that is submitted to the workload manager

    Returns:
    ========
    Instance of a workload manager object
    """
    job_object = _get_job_object(system)
    source = source.expanduser().absolute()
    if source.exists():
        env_extra = [f"\\. {source}"]
    else:
        env_extra = []
    try:
        options = dict(
            name=config["name"],
            memory=config.get("memory", "128GB"),
            walltime=config.get("walltime", "08:00:00"),
            job_cpu=int(config.get("cpus", 4)),
            queue=config["queue"],
            project=config["project"],
            log_directory=log_directory,
            job_extra=config.get("extra_options", []),
            freva_args=config.get("args"),
            delete_job_script=delete_job_script,
            env_extra=env_extra,
        )
    except KeyError:
        raise ValueError("Scheduler options not properly configured")
    job = job_object(**options)
    job.start()
    job_name = job.job_name or "worker"
    job_out = Path(log_directory) / f"{job_name}-{job.job_id}.out"
    return job.job_id, str(job_out.absolute())
