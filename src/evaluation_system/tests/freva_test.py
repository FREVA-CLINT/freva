"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import evaluation_system.settings.database
import unittest
import os
import tempfile
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)

# load the test configuration before anything else
os.environ['EVALUATION_SYSTEM_CONFIG_FILE']= os.path.dirname(__file__) + '/test.conf'

from evaluation_system.tests.capture_std_streams import stdout
import evaluation_system.api.plugin_manager as pm
from evaluation_system.tests.mocks.dummy import DummyPlugin
from evaluation_system.api.parameters import ParameterDictionary, Integer, String,\
    ValidationError
from evaluation_system.api.plugin_manager import PluginManagerException
from evaluation_system.model.user import User


def load_lib(module_file_path):
    """Loads a module from a file not ending in .py"""
    # Try to tell python not to write these compiled files to disk
    import sys
    sys.dont_write_bytecode = True
    
    import imp
    
    py_source_open_mode = "U"
    py_source_description = (".py", py_source_open_mode, imp.PY_SOURCE)
    
    module_name = os.path.basename(module_file_path)
    with open(module_file_path, py_source_open_mode) as module_file:
        return imp.load_module(
                module_name, module_file, module_file_path, py_source_description)

# load the module from a non .py file
Freva = load_lib(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../bin/freva')))
tools_dir = os.path.join(__file__[:-len('src/evaluation_system/tests/analyze_test.py')-1], 'tools')


def call(cmd_string):
    """Simplify the interaction with the shell.
    Parameters
    cmd_string : string
        the command to be issued in a string"""
    from subprocess import Popen, PIPE, STDOUT
    # workaround: the script test for PS1, setting it makes it believe we are in an interactive shell
    cmd_string = 'export PS1=x; . /etc/bash.bashrc >/dev/null;' + cmd_string
    p = Popen(['/bin/bash', '-c', '%s' % cmd_string], stdout=PIPE, stderr=STDOUT)
    return p.communicate()[0]


class Test(unittest.TestCase):
    def setUp(self):
        pm.reloadPlugins()
        self.freva = Freva.Freva()

    def test_list_commands(self):
        stdout.startCapturing()
        stdout.reset()
        self.freva.auto_doc()
        stdout.stopCapturing()
        freva_commands = stdout.getvalue()
        self.assertIn('--plugin', freva_commands)
        self.assertIn('--history', freva_commands)
        self.assertIn('--databrowser', freva_commands)
        self.assertIn('--crawl_my_data', freva_commands)
        self.assertIn('--esgf', freva_commands)