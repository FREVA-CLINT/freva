"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import logging
import sys
from subprocess import run, PIPE
import shlex
import pytest
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)


def test_list_commands(freva_lib, stdout):
    import evaluation_system.settings.database
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

def test_run():
    from evaluation_system.commands import _main as freva
    cmd = [sys.executable, freva.__file__]
    res = run(cmd, stdout=PIPE, stderr=PIPE)
    freva_commands = res.stdout.decode()
    assert '--plugin' in freva_commands
    assert '--history' in freva_commands
    assert '--databrowser' in freva_commands
    assert '--crawl_my_data' in freva_commands
    assert '--esgf' in freva_commands
    cmd = [sys.executable, freva.__file__, '-h', '-d']
    res = run(cmd, stdout=PIPE, stderr=PIPE)
    freva_commands = res.stdout.decode()
    assert '--plugin' in freva_commands
    assert '--history' in freva_commands
    assert '--databrowser' in freva_commands
    assert '--crawl_my_data' in freva_commands
    assert '--esgf' in freva_commands
    cmd = [sys.executable, freva.__file__, '--esgf', '-h', '-d']
    res = run(cmd, stdout=PIPE, stderr=PIPE)
    out = res.stdout.decode()
    assert 'esgf' in out.lower()

def test_admin_cmd():
    from evaluation_system.commands.admin.update_tool_doc import Command
    from evaluation_system.commands._main import Freva
    freva = Freva()
    assert freva._load_command('update_tool_doc') == Command
    with pytest.raises(ImportError):
        freva._load_command(object)



