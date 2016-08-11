"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import os
import unittest
from evaluation_system.misc import config
import logging
from evaluation_system.commands.crawl_my_data import Command
from evaluation_system.tests.capture_std_streams import stdout
import sys


class BaseCommandTest(unittest.TestCase):
    
    def setUp(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        print os.path.dirname(__file__) + '/test.conf'
        config.reloadConfiguration()
        self.cmd = Command()

    def test_auto_doc(self):
        stdout.startCapturing()
        stdout.reset()
        with self.assertRaises(SystemExit):
            self.cmd.run(['--help'])
        stdout.stopCapturing()
        doc_str = stdout.getvalue()
        self.assertEqual(doc_str, '''Use this command to update your projectdata.

Usage: %s %s [options]

Options:
  -d, --debug  turn on debugging info and show stack trace on exceptions.
  -h, --help   show this help message and exit
  --path=PATH  crawl the given directory
''' % (os.path.basename(sys.argv[0]), sys.argv[1]))

    def test_crawl_my_data(self):
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run([])
        stdout.stopCapturing()
        output = stdout.getvalue()
        self.assertIn('Please wait while the system is crawling your data', output)
        self.assertIn('Finished', output)
        self.assertIn('Crawling took', output)

        with self.assertRaises(SystemExit):
            self.assertRaises(self.cmd.run(['--path=/tmp/forbidden/folder']))