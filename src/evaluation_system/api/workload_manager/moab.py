"""Submit jobs using the moab workload manager."""

from __future__ import annotations

from typing import ClassVar

from .pbs import PBSJob


class MoabJob(PBSJob):
    submit_command: ClassVar[str] = "msub"
    cancel_command: ClassVar[str] = "canceljob"
    config_name: ClassVar[str] = "moab"
