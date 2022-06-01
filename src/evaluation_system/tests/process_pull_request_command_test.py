"""
Created on 28.06.2016

@author: Sebastian Illing
"""
import logging
import mock
import os
from pathlib import Path
import pytest
import sys
import shutil

from git import Repo, Tag

from evaluation_system.tests import run_cli
from evaluation_system.tests import mockenv


def test_command_fail(capsys, admin_env, caplog):
    from evaluation_system.model.plugins.models import ToolPullRequest
    from django.contrib.auth.models import User

    # add an entry to pull-requests
    with mockenv(**admin_env):
        pr = ToolPullRequest.objects.create(
            tool="murcss",
            tagged_version="1.0",
            user=User.objects.first(),
            status="waiting",
        )
        # Clear all previous logs
        run_cli("check pull-request")
        # Get the last log on record
        _, loglevel, message = caplog.record_tuples[-1]
        assert loglevel == logging.ERROR
        assert message == "Plugin murcss does not exist"
        new_pr = ToolPullRequest.objects.get(id=pr.id)
        assert new_pr.status == "failed"


def test_command_success(capsys, dummy_git_path, git_config, admin_env):

    from evaluation_system.api import plugin_manager as pm
    from evaluation_system.model.plugins.models import ToolPullRequest
    from django.contrib.auth.models import User

    with mockenv(**admin_env):
        repo_path, tool_path = dummy_git_path
        this_dir = Path(__file__).parent
        shutil.copy(this_dir / "mocks" / "result_tags.py", repo_path)
        # prepare git repo
        os.system(
            (
                f"cd {repo_path}; git init; git config user.name tmp_user; "
                f"git config user.email test@testing.com; {git_config}"
            )
        )
        os.system('cd %s; git add *; git commit -m "first commit" ' % (repo_path))
        # clone it
        os.system("git clone %s %s" % (repo_path, tool_path))
        # create a new tag
        os.system('cd %s; git tag -a v2.0 -m "new tag"' % (repo_path))
        # add plugin to system
        with mock.patch.dict(
            os.environ, {"EVALUATION_SYSTEM_PLUGINS": f"{tool_path},result_tags"}
        ):
            pm.reload_plugins()
            repository = Repo(tool_path)
            assert len(repository.tags) == 0

            pr = ToolPullRequest.objects.create(
                tool="resulttagtest",
                tagged_version="v2.0",
                user=User.objects.first(),
                status="waiting",
            )
            # finally run the command
            run_cli("check pull-request")
            cmd_out = capsys.readouterr().out
            assert "Processing pull request for resulttagtest by" in cmd_out
            new_pr = ToolPullRequest.objects.get(id=pr.id)
            assert new_pr.status == "success"
            assert repository.tags[0].name == "v2.0"
            assert len(repository.tags) == 1


def test_get_version(admin_env):
    from evaluation_system.model.repository import get_version

    # self version test
    version = get_version(".")
    assert len(version) == 2

    not_versioned = get_version("/tmp")
    assert not_versioned == ("unknown", "unknown")


def test_forbidden_usage(dummy_env):
    from freva.cli.admin.check import check4pull_request

    with pytest.raises(RuntimeError):
        check4pull_request()

    with pytest.raises(SystemExit):
        with pytest.raises(RuntimeError):
            run_cli("check pull-request")
