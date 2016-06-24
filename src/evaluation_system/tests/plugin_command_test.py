"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import os
import unittest
from evaluation_system.commands.plugin import Command
from evaluation_system.tests.capture_std_streams import stdout
from evaluation_system.misc import config
from evaluation_system.api import plugin_manager as pm
from evaluation_system.model.history.models import History
import sys


class BaseCommandTest(unittest.TestCase):
    
    def setUp(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        config.reloadConfiguration()
        pm.reloadPlugins()
        self.cmd = Command()

    def tearDown(self):
        if config._DEFAULT_ENV_CONFIG_FILE in os.environ:
            del os.environ[config._DEFAULT_ENV_CONFIG_FILE]

    def test_list_tools(self):
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run([])
        stdout.stopCapturing()
        plugin_list = stdout.getvalue()
        self.assertIn('DummyPlugin: A dummy plugin\n', plugin_list)

    def test_help(self):
        stdout.startCapturing()
        stdout.reset()
        with self.assertRaises(SystemExit):
            self.cmd.run(['--help'])
        stdout.stopCapturing()
        help_str = stdout.getvalue()

        self.assertEqual(help_str, '''Applies some analysis to the given data.
See https://code.zmaw.de/projects/miklip-d-integration/wiki/Analyze for more information.

The "query" part is a key=value list used for configuring the tool. It's tool dependent so check that tool help.

For Example:
    freva --plugin pca eofs=4 bias=False input=myfile.nc outputdir=/tmp/test

Usage: %s %s [options]

Options:
  -d, --debug           turn on debugging info and show stack trace on
                        exceptions.
  -h, --help            show this help message and exit
  --repos-version       show the version number from the repository
  --caption=CAPTION     sets a caption for the results
  --save                saves the configuration locally for this user.
  --save-config=FILE    saves the configuration at the given file path
  --show-config         shows the resulting configuration (implies dry-run).
  --scheduled-id=ID     Runs a scheduled job from database
  --dry-run             dry-run, perform no computation. This is used for
                        viewing and handling the configuration.
  --batchmode=BOOL      creates a SLURM job
  --unique_output=BOOL  If true append the freva run id to every output folder
''' % (os.path.basename(sys.argv[0]), sys.argv[1]))

        stdout.startCapturing()
        stdout.reset()
        with self.assertRaises(SystemExit):
            self.cmd.run(['dummyplugin', '--help'])
        stdout.stopCapturing()
        help_str = stdout.getvalue()
        self.assertEqual(help_str, '''DummyPlugin (v0.0.0): A dummy plugin
Options:
number     (default: <undefined>)
           This is just a number, not really important
the_number (default: <undefined>) [mandatory]
           This is *THE* number. Please provide it
something  (default: test)
           No help available.
other      (default: 1.4)
           No help available.
input      (default: <undefined>)
           No help available.
''')

    def test_run_plugin(self):

        # test missing parameter
        stdout.startCapturing()
        stdout.reset()
        with self.assertRaises(SystemExit):
            self.cmd.run(['dummyplugin'])
        stdout.stopCapturing()
        help_str = stdout.getvalue()
        self.assertIn('Error found when parsing parameters. Missing mandatory parameters: the_number', help_str)

        # test run tool
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(['dummyplugin', 'the_number=32', '--caption="Some caption"'])
        stdout.stopCapturing()
        output_str = stdout.getvalue()
        self.assertIn('Dummy tool was run with: {\'input\': None, \'other\': 1.4, \'number\': None, \'the_number\': 32, \'something\': \'test\'}', output_str)

        # test get version
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(['dummyplugin', '--repos-version'])
        stdout.stopCapturing()
        output_str = stdout.getvalue()

        # test batch mode
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(['dummyplugin', '--batchmode=True', 'the_number=32'])
        stdout.stopCapturing()
        output_str = stdout.getvalue()

        # test save config
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(['dummyplugin', 'the_number=32', '--save'])
        stdout.stopCapturing()
        output_str = stdout.getvalue()
        fn = '/home/illing/evaluation_system/config/dummyplugin/dummyplugin.conf'
        self.assertTrue(os.path.isfile(fn))
        os.remove(fn)

        # test show config
        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(['dummyplugin', 'the_number=42', '--show-config'])
        stdout.stopCapturing()
        output_str = stdout.getvalue()
        self.assertEqual(output_str, '''    number: -
the_number: 42
 something: test
     other: 1.4
     input: -
''')

        # remove all history entries
        History.objects.all().delete()
