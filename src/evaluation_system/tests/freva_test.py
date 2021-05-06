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
