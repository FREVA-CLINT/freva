"""
Created on 28.06.2016

@author: Sebastian Illing
"""
import os
from pathlib import Path
import sys
import shutil

from git import Repo, Tag
import pytest

from evaluation_system.tests import run_command_with_capture

def test_command_fail(dummy_pr, stdout):
    from evaluation_system.model.plugins.models import ToolPullRequest
    from django.contrib.auth.models import User
    # add an entry to pull-requests
    pr = ToolPullRequest.objects.create(
        tool='murcss',
        tagged_version='1.0',
        user=User.objects.first(),
        status='waiting'
    )
    sys.stdout = stdout
    stdout.startCapturing()
    stdout.reset()
    with pytest.raises(SystemExit):
        dummy_pr.run([])
    stdout.stopCapturing()
    cmd_out = stdout.getvalue()
    new_pr = ToolPullRequest.objects.get(id=pr.id)
    assert new_pr.status == 'failed'
    assert 'ERROR:   Plugin murcss does not exist' in cmd_out

def test_command_success(dummy_pr, stdout, dummy_git_path, git_config):

    from evaluation_system.api import plugin_manager as pm
    from evaluation_system.model.plugins.models import ToolPullRequest
    from django.contrib.auth.models import User
    repo_path, tool_path = dummy_git_path
    this_dir = Path(__file__).parent
    shutil.copy(this_dir / 'mocks' / 'result_tags.py', repo_path)
    # prepare git repo

    os.system('cd %s; git init; %s'%(repo_path, git_config))
    os.system('cd %s; git add *; git commit -m "first commit" ' % (repo_path))
    # clone it
    os.system('git clone %s %s' % (repo_path, tool_path))
    # create a new tag
    os.system('cd %s; git tag -a v2.0 -m "new tag"' % (repo_path))
    # add plugin to system
    os.environ['EVALUATION_SYSTEM_PLUGINS'] = f'{tool_path},result_tags'
    pm.reloadPlugins()
    repository = Repo(tool_path)
    assert len(repository.tags) == 0

    pr = ToolPullRequest.objects.create(
        tool='resulttagtest',
        tagged_version='v2.0',
        user=User.objects.first(),
        status='waiting'
    )
    # finally run the command
    cmd_out = run_command_with_capture(dummy_pr, stdout,)

    assert 'Processing pull request for resulttagtest by' in cmd_out
    new_pr = ToolPullRequest.objects.get(id=pr.id)
    assert new_pr.status == 'success'
    assert repository.tags[0].name == 'v2.0'
    assert len(repository.tags) == 1

def test_get_version():
    from evaluation_system.model.repository import getVersion
    # self version test
    version = getVersion('.')
    assert len(version) == 2

    not_versioned = getVersion('/tmp')
    assert not_versioned == ('unknown', 'unknown')
