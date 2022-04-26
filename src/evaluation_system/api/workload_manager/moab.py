"""Submit jobs using the moab workload manager."""
from __future__ import annotations
from .pbs import PBSJob
from typing import ClassVar


class MoabJob(PBSJob):
    submit_command: ClassVar[str] = "msub"
    cancel_command: ClassVar[str] = "canceljob"
    config_name: ClassVar[str] = "moab"
