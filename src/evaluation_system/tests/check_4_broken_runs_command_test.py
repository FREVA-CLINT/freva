"""
Created on 11.08.2016

@author: Sebastian Illing
"""
import os
import unittest
from evaluation_system.commands.admin.check_4_broken_runs import Command
from evaluation_system.tests.capture_std_streams import stdout
from evaluation_system.misc import config
from evaluation_system.api import plugin_manager as pm
from evaluation_system.model.history.models import History
from django.contrib.auth.models import User
import datetime


class BaseCommandTest(unittest.TestCase):
    
    def setUp(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        config.reloadConfiguration()
        pm.reloadPlugins()
        self.cmd = Command()

    def test_command(self):
        # add a "broken" but running job to db
        broken_obj = History.objects.create(
            status=History.processStatus.running,
            slurm_output='/some/out.txt',
            timestamp=datetime.datetime.now(),
            uid=User.objects.first()
        )
        History.objects.create(
            status=History.processStatus.finished,
            slurm_output='/some/out.txt',
            timestamp=datetime.datetime.now(),
            uid=User.objects.first()
        )
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run([])
        stdout.stopCapturing()
        cmd_out = stdout.getvalue()
        self.assertEqual(cmd_out, 'Setting job %s to broken\n' % broken_obj.id)
        self.assertEqual(History.objects.get(id=broken_obj.id).status, History.processStatus.broken)
