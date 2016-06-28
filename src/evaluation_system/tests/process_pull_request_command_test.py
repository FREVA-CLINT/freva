"""
Created on 28.06.2016

@author: Sebastian Illing
"""
import os
import unittest
from evaluation_system.commands.admin.process_pull_requests import Command
from evaluation_system.tests.capture_std_streams import stdout
from evaluation_system.misc import config
from django.contrib.auth.models import User
from evaluation_system.api import plugin_manager as pm
from evaluation_system.model.history.models import History
from evaluation_system.model.plugins.models import ToolPullRequest
import sys
import shutil
from git import Repo, Tag


class BaseCommandTest(unittest.TestCase):
    
    def setUp(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        config.reloadConfiguration()
        pm.reloadPlugins()
        self.cmd = Command()

    def tearDown(self):
        ToolPullRequest.objects.all().delete()
        if config._DEFAULT_ENV_CONFIG_FILE in os.environ:
            del os.environ[config._DEFAULT_ENV_CONFIG_FILE]

    def test_command_fail(self):
        # add an entry to pull-requests
        pr = ToolPullRequest.objects.create(
            tool='murcss',
            tagged_version='1.0',
            user=User.objects.first(),
            status='waiting'
        )
        stdout.startCapturing()
        stdout.reset()
        with self.assertRaises(SystemExit):
            self.cmd.run([])
        stdout.stopCapturing()
        cmd_out = stdout.getvalue()
        new_pr = ToolPullRequest.objects.get(id=pr.id)
        self.assertEqual(new_pr.status, 'failed')
        self.assertIn('ERROR:   Plugin murcss does not exist', cmd_out)

    def test_command_success(self):

        repo_path = '/tmp/test_plugin.git'
        tool_path = '/tmp/test_tool'
        os.makedirs(repo_path)
        shutil.copy('tests/mocks/result_tags.py', repo_path)
        # prepare git repo
        os.system('cd %s; git init; git add *; git commit -m "first commit" ' % (repo_path))
        # clone it
        os.system('git clone %s %s' % (repo_path, tool_path))
        # create a new tag
        os.system('cd %s; git tag -a v2.0 -m "new tag"' % (repo_path))
        # add plugin to system
        os.environ['EVALUATION_SYSTEM_PLUGINS'] = '/tmp/test_tool,result_tags'
        pm.reloadPlugins()
        repository = Repo(tool_path)
        self.assertEqual(len(repository.tags), 0)

        pr = ToolPullRequest.objects.create(
            tool='resulttagtest',
            tagged_version='v2.0',
            user=User.objects.first(),
            status='waiting'
        )
        # finally run the command
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run([])
        stdout.stopCapturing()
        cmd_out = stdout.getvalue()

        self.assertIn('Processing pull request for resulttagtest by', cmd_out)
        new_pr = ToolPullRequest.objects.get(id=pr.id)
        self.assertEqual(new_pr.status, 'success')
        self.assertEqual(repository.tags[0].name, 'v2.0')
        self.assertEqual(len(repository.tags), 1)
        shutil.rmtree(repo_path)
        shutil.rmtree(tool_path)
