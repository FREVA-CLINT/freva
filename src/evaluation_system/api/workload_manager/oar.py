"""Submit jobs using the oar workload manager."""
from __future__ import annotations
import logging
import shlex
from typing import Optional, Union, ClassVar

from .core import Job

logger = logging.getLogger(__name__)


class OARJob(Job):

    # Override class variables
    submit_command: ClassVar[str] = "oarsub"
    cancel_command: ClassVar[str] = "oardel"
    job_id_regexp: ClassVar[str] = r"OAR_JOB_ID=(?P<job_id>\d+)"
    config_name: ClassVar[str] = "oar"

    def __init__(
        self,
        scheduler: Optional[str] = None,
        name: Optional[str] = None,
        queue: Optional[str] = None,
        project: Optional[str] = None,
        resource_spec: Optional[str] = None,
        walltime: str = "",
        job_extra: Optional[list[str]] = None,
        **base_class_kwargs,
    ):
        super().__init__(scheduler=scheduler, name=name, **base_class_kwargs)
        job_extra = job_extra or []
        header_lines = []
        if self.job_name is not None:
            header_lines.append("#OAR -n %s" % self.job_name)
        if queue is not None:
            header_lines.append("#OAR -q %s" % queue)
        if project is not None:
            header_lines.append("#OAR --project %s" % project)

        # OAR needs to have the resource on a single line otherwise it is
        # considered as a "moldable job" (i.e. the scheduler can chose between
        # multiple sets of resources constraints)
        resource_spec_list = []
        if resource_spec is None:
            # default resource_spec if not specified. Crucial to specify
            # nodes=1 to make sure the cores allocated are on the same node.
            resource_spec = "/nodes=1/core=%d" % self.worker_cores
        resource_spec_list.append(resource_spec)
        if walltime is not None:
            resource_spec_list.append("walltime=%s" % walltime)

        full_resource_spec = ",".join(resource_spec_list)
        header_lines.append("#OAR -l %s" % full_resource_spec)
        header_lines.extend(["#OAR %s" % arg for arg in job_extra])

        self.job_header = "\n".join(header_lines)

        logger.debug("Job script: \n %s" % self.job_script())

    async def _submit_job(self, fn):
        # OAR specificity: the submission script needs to exist on the worker
        # when the job starts on the worker. This is different from other
        # schedulers that only need the script on the submission node at
        # submission time. That means that we can not use the same strategy as
        # in JobQueueCluster: create a temporary submission file, submit the
        # script, delete the submission file. In order to reuse the code in
        # the base JobQueueCluster class, we read from the temporary file and
        # reconstruct the command line where the script is passed in as a
        # string (inline script in OAR jargon) rather than as a filename.
        with open(fn) as f:
            content_lines = f.readlines()

        oar_lines = [line for line in content_lines if line.startswith("#OAR ")]
        oarsub_options = [line.replace("#OAR ", "").strip() for line in oar_lines]
        inline_script_lines = [
            line for line in content_lines if not line.startswith("#")
        ]
        inline_script = "".join(inline_script_lines)
        oarsub_command = " ".join([self.submit_command] + oarsub_options)
        oarsub_command_split = shlex.split(oarsub_command) + [inline_script]
        return self._call(oarsub_command_split)
