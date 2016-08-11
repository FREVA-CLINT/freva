"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import os
import datetime
import unittest
import pwd
from evaluation_system.commands.history import Command
from evaluation_system.tests.capture_std_streams import stdout
from evaluation_system.misc import config
from evaluation_system.api import plugin_manager as pm
from evaluation_system.model.history.models import History
from evaluation_system.model.user import User
from evaluation_system.tests.mocks.dummy import DummyUser, DummyPlugin
import sys


class BaseCommandTest(unittest.TestCase):

    def setUp(self):
        uid = os.getuid()
        self.udata = pwd.getpwuid(uid)
        self.user = DummyUser(random_home=True, **{'pw_name': self.udata.pw_name})
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        config.reloadConfiguration()
        pm.reloadPlugins()
        self.cmd = Command()

    def tearDown(self):
        if config._DEFAULT_ENV_CONFIG_FILE in os.environ:
            del os.environ[config._DEFAULT_ENV_CONFIG_FILE]

        # delete all history entries
        History.objects.filter(uid_id=self.udata.pw_name).delete()

    def test_history(self):

        hist_ids = []
        for i in range(10):
            hist_ids += [self.user.getUserDB().storeHistory(
                tool=DummyPlugin(),
                config_dict={'the_number': 42, 'number': 12, 'something': 'else', 'other': 'value', 'input': '/folder'},
                status=0,
                uid=self.udata.pw_name
            )]

        # test history output
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run([])
        stdout.stopCapturing()
        output_str = stdout.getvalue()
        self.assertEqual(output_str.count('dummyplugin'), 10)
        self.assertEqual(output_str.count('\n'), 10)

        # test limit output
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(['--limit=3'])
        stdout.stopCapturing()
        output_str = stdout.getvalue()
        self.assertEqual(output_str.count('dummyplugin'), 3)
        self.assertEqual(output_str.count('\n'), 3)

        # test return_command option
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(['--entry_ids=%s' % hist_ids[0], '--return_command'])
        stdout.stopCapturing()
        output_str = stdout.getvalue()
        self.assertIn('--plugin dummyplugin something=\'else\' input=\'/folder\' other=\'value\' number=\'12\' the_number=\'42\'', output_str)