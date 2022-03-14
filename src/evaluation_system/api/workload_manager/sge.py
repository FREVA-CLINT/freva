import logging

from .core import Job

logger = logging.getLogger(__name__)


class SGEJob(Job):
    submit_command = "qsub"
    cancel_command = "qdel"
    config_name = "sge"

    def __init__(
        self,
        name=None,
        queue=None,
        project=None,
        resource_spec=None,
        walltime=None,
        job_extra=[],
        **base_class_kwargs,
    ):
        super().__init__(name=name, **base_class_kwargs)

        header_lines = []
        if self.job_name is not None:
            header_lines.append("#$ -N %(job-name)s")
        if queue is not None:
            header_lines.append("#$ -q %(queue)s")
        if project is not None:
            header_lines.append("#$ -P %(project)s")
        if resource_spec is not None:
            header_lines.append("#$ -l %(resource_spec)s")
        if walltime is not None:
            header_lines.append("#$ -l h_rt=%(walltime)s")
        if self.log_directory is not None:
            header_lines.append("#$ -e %(log_directory)s/")
            header_lines.append("#$ -o %(log_directory)s/")
        header_lines.extend(["#$ -cwd", "#$ -j y"])
        header_lines.extend(["#$ %s" % arg for arg in job_extra])
        header_template = "\n".join(header_lines)

        config = {
            "job-name": self.job_name,
            "queue": queue,
            "project": project,
            "processes": self.worker_processes,
            "walltime": walltime,
            "resource_spec": resource_spec,
            "log_directory": self.log_directory,
        }
        self.job_header = header_template % config

        logger.debug("Job script: \n %s" % self.job_script())
