"""Collection of methods and classes for submitting plugins to a workload manager."""
from __future__ import annotations
from pathlib import Path
from typing import cast, Union, Type, List, Optional
from .core import Job
from .local import LocalJob
from .lsf import LSFJob
from .moab import MoabJob
from .oar import OARJob
from .pbs import PBSJob
from .sge import SGEJob
from .slurm import SLURMJob


def get_job_class(system: str) -> Type[Job]:
    """Get the correct job scheduler object for a given workload manager.

    Parameters
    -----------
    system: str
        Name of the scheduling system

    Returns
    -------
    evaluation_system.api.workload_manager.core:
        Job class corresponding to the scheuler system.

    """
    job_objects: dict[str, Type[Job]] = dict(
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
    job_object = get_job_class(system)
    return f"{job_object.cancel_command} {job_id}"


def schedule_job(
    system: str,
    source: Path,
    config: dict[str, Union[str, list[str]]],
    log_directory: Union[Path, str],
    delete_job_script: bool = True,
    config_file: Optional[Path] = None,
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
    job_object: Type[Job] = get_job_class(system)
    source = source.expanduser().absolute()
    ncpus = int(cast(str, config.get("cpus", "4")))
    if source.exists():
        env_extra = [f"source {source}"]
    else:
        env_extra = []
    if config_file:
        env_extra.append(f"export EVALUATION_SYSTEM_CONFIG_FILE={config_file}")
    try:
        job = job_object(
            name=cast(str, config["name"]),
            memory=cast(str, config.get("memory", "128GB")),
            walltime=cast(str, config.get("walltime", "08:00:00")),
            job_cpu=ncpus,
            queue=config["queue"],
            project=config["project"],
            log_directory=log_directory,
            job_extra=config.get("extra_options", []),
            freva_args=cast(List[str], config.get("args")),
            delete_job_script=delete_job_script,
            env_extra=env_extra,
        )
    except KeyError:
        raise ValueError("Scheduler options not properly configured")
    job.start()
    job_name = job.job_name or "worker"
    job_out = Path(log_directory) / f"{job_name}-{job.job_id}.out"
    return int(job.job_id), str(job_out.absolute())
