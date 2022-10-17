"""Collection of admin commands that perform checks."""
from __future__ import annotations
import argparse
import os
from typing import Any

import lazy_import
from ..utils import subparser_func_type
from evaluation_system.misc import logger
from ..utils import BaseParser, is_admin
from evaluation_system.misc.exceptions import CommandError

History = lazy_import.lazy_class("evaluation_system.model.history.models.History")
pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")


__all__ = ["check4broken_runs"]

CLI = "CheckCli"


def check4broken_runs() -> None:
    """Check for broken runs in SLURM"""

    is_admin(raise_error=True)
    running_jobs = History.objects.filter(status=History.processStatus.running).exclude(
        slurm_output=0
    )
    for job in running_jobs:
        slurm_status = job.get_slurm_status()
        if (
            "cancelled" in slurm_status.lower()
            or "timeout" in slurm_status.lower()
            or "fail" in slurm_status.lower()
        ):
            print(slurm_status, job.tool)
            print(f"Setting job {job.id} to broken")
            job.status = job.processStatus.broken
            job.save()
        elif "completed" in slurm_status.lower():
            job.status = job.processStatus.finished
            job.save()


class BrokenRun(BaseParser):
    """Command line interface to check for broken runs in batchmode."""

    desc = "Check for broken runs and report them."

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        """Construct the sub arg. parser."""

        self.parser = parser
        parser.add_argument(
            "--debug",
            "--verbose",
            help="Use verbose output.",
            action="store_true",
            default=False,
        )
        self.logger.setLevel(20)  # Set log level to info
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs: Any) -> None:
        """Apply the check4broken_runs method"""

        check4broken_runs()


class CheckCli(BaseParser):
    """Interface defining parsers to perform checks."""

    desc = "Perform various checks."

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        """Construct the sub arg. parser."""

        sub_commands: dict[str, subparser_func_type] = {
            "broken-runs": self.parse_broken_runs,
        }
        super().__init__(sub_commands, parser)
        # This parser doesn't do anything without a sub-commands
        # hence the default function should just print the usage
        self.parser.set_defaults(apply_func=self._usage)

    @staticmethod
    def parse_broken_runs(subparsers: argparse._SubParsersAction) -> BrokenRun:
        sub_parser = subparsers.add_parser(
            "broken-runs",
            description="Check for broken runs and report them.",
            help="Check for broken runs and report them.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        return BrokenRun(sub_parser)
