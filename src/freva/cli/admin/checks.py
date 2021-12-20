"""Collection of admin commands that perform checks."""

__all__ = ["check4broken_runs", "check4pull_request"]

import argparse
import os


from ..utils import BaseParser, parse_type, is_admin

from evaluation_system.misc import logger
from evaluation_system.misc.exceptions import CommandError
from evaluation_system.model.history.models import History
from evaluation_system.model.plugins.models import ToolPullRequest
from evaluation_system.api import plugin_manager as pm


def check4pull_request() -> None:
    """Check for pending pull requests."""

    is_admin(raise_error=True)
    pull_requests = ToolPullRequest.objects.filter(status="waiting")
    tools = pm.getPlugins()
    for request in pull_requests:
        print(f"Processing pull request for {request.tool} by {request.user}")
        request.status = "processing"
        request.save()
        tool_name = request.tool.lower()
        if tool_name not in tools.keys():
            request.status = "failed"
            request.save()
            logger.error(f"Plugin {request.tool} does not exist")
            return
        # get repo path
        path = "/".join(tools[tool_name]["plugin_module"].split("/")[:-1])
        exit_code = os.system(
            "cd %s; git pull; git checkout -b version_%s %s"
            % (path, request.tagged_version, request.tagged_version)
        )
        if exit_code > 1:
            # Probably branch exists already
            # Try to checkout old branch
            exit_code = os.system(
                "cd %s; git checkout version_%s " % (path, request.tagged_version)
            )
            if exit_code > 1:
                raise CommandError("Something went wrong, please contact the admins")
        request.status = "success"
        request.save()


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


class CheckCli(BaseParser):
    """Interface defining parsers to perform checks."""

    desc = "Perform various checks."

    def __init__(self, parser: parse_type) -> None:
        """Construct the sub arg. parser."""

        sub_commands = ("broken-runs", "pull-request")
        super().__init__(sub_commands, parser)
        # This parser doesn't do anything without a sub-commands
        # hence the default function should just print the usage
        self.parser.set_defaults(apply_func=self._usage)

    def parse_pull_request(self) -> None:
        sub_parser = self.subparsers.add_parser(
            "pull-request",
            description=PullRequest.desc,
            help=PullRequest.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        PullRequest(sub_parser)

    def parse_broken_runs(self) -> None:
        sub_parser = self.subparsers.add_parser(
            "broken-runs",
            description=BrokenRun.desc,
            help=BrokenRun.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        BrokenRun(sub_parser)


class PullRequest(BaseParser):
    """Command line interface to check for incoming PR's"""

    desc = "Check for incoming pull requests."

    def __init__(self, parser: parse_type) -> None:
        """Construct the sub arg. parser."""

        parser.add_argument(
            "--debug",
            "-v",
            help="use verbose output.",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--deamon", help="Spawn in daemon mode", action="store_true", default=False
        )
        self.parser = parser
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs) -> None:
        """Apply the check4broken_runs method"""

        check4pull_request()


class BrokenRun(BaseParser):
    """Command line interface to check for broken runs in batchmode."""

    desc = "Check for broken runs and report them."

    def __init__(self, parser: parse_type) -> None:
        """Construct the sub arg. parser."""

        parser.add_argument(
            "--debug",
            "-d",
            "-v",
            help="use verbose output.",
            action="store_true",
            default=False,
        )
        self.parser = parser
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(args: argparse.Namespace, **kwargs) -> None:
        """Apply the check4broken_runs method"""

        check4broken_runs()
