"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import os
import unittest
from evaluation_system.misc import config
import logging
from evaluation_system.misc.config import (ConfigurationException,
                                           reloadConfiguration)
from evaluation_system.commands import FrevaBaseCommand
from evaluation_system.tests.capture_std_streams import stdout

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)

import sys


class DummyCommand(FrevaBaseCommand):
    __short_description__ = '''This is a test dummy'''
    __description__ = __short_description__

    _args = [
        {'name': '--debug', 'short': '-d', 'help': 'turn on debugging info and show stack trace on exceptions.',
         'action': 'store_true'},
        {'name': '--help', 'short': '-h', 'help': 'show this help message and exit', 'action': 'store_true'},
        {'name': '--input', 'help': 'Some input value', 'metavar': 'PATH'},
    ]

    def _run(self,*args,**kwargs):
        print 'The answer is %s' % self.args.input


class BaseCommandTest(unittest.TestCase):
    
    def tearDown(self):
        if config._DEFAULT_ENV_CONFIG_FILE in os.environ:
            del os.environ[config._DEFAULT_ENV_CONFIG_FILE]
        config.reloadConfiguration()

    def test_auto_doc(self):
        stdout.startCapturing()
        stdout.reset()
        with self.assertRaises(SystemExit):
            DummyCommand().run(['--help'])
        stdout.stopCapturing()
        doc_str = stdout.getvalue()

        self.assertEqual(doc_str, '''This is a test dummy

Usage: %s %s [options]

Options:
  -d, --debug   turn on debugging info and show stack trace on exceptions.
  -h, --help    show this help message and exit
  --input=PATH  Some input value
''' % (os.path.basename(sys.argv[0]), sys.argv[1]))

    def test_bad_option(self):
        stdout.startCapturing()
        stdout.reset()
        with self.assertRaises(SystemExit):
            DummyCommand().run(['--input1'])
        stdout.stopCapturing()
        help_out =  stdout.getvalue()
        self.assertIn('''Did you mean this?\n\tinput''', help_out)

    def test_dummy_command(self):
        stdout.startCapturing()
        stdout.reset()
        DummyCommand().run(['--input=10', '-d'])
        stdout.stopCapturing()
        command_out =  stdout.getvalue()
        self.assertEqual(command_out, 'The answer is 10\n')
