"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import evaluation_system.settings.database
import unittest
import os
import tempfile
import logging
import sys
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)

# load the test configuration before anything else
#from evaluation_system.tests.capture_std_streams import stdout
#import evaluation_system.api.plugin_manager as pm
#from evaluation_system.tests.mocks.dummy import DummyPlugin
#from evaluation_system.api.parameters import ParameterDictionary, Integer, String,\
#    ValidationError
#from evaluation_system.api.plugin_manager import PluginManagerException
#from evaluation_system.model.user import User


#tools_dir = os.path.join(__file__[:-len('src/evaluation_system/tests/analyze_test.py')-1], 'tools')


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



def test_list_commands(freva_lib, stdout):
    sys.stdout = stdout
    stdout.startCapturing()
    stdout.reset()
    freva_lib.auto_doc()
    freva_commands = stdout.getvalue()
    stdout.stopCapturing()
    assert '--plugin' in freva_commands
    assert '--history' in freva_commands
    assert '--databrowser' in freva_commands
    assert '--crawl_my_data' in freva_commands
    assert '--esgf' in freva_commands
