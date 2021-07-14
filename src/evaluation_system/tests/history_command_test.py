"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import os
import datetime
import pwd
import sys
import pytest

def test_freva_history_method(dummy_history, dummy_user):
    from freva import history
    from evaluation_system.tests.mocks.dummy import DummyPlugin
    from evaluation_system.commands.history import Command
    from evaluation_system.tests import run_command_with_capture
    config_dict={'the_number': 42, 'number': 12, 'something': 'else', 'other': 'value', 'input': '/folder'}
    hist_ids = []
    uid = os.getuid()
    udata = pwd.getpwuid(uid)
    for i in range(10):
        hist_ids += [dummy_user.user.getUserDB().storeHistory(
            tool=DummyPlugin(),
            config_dict=config_dict,
            status=0,
            uid=udata.pw_name
        )]
    hist = history()
    assert isinstance(hist, (list, tuple))
    assert len(hist) == 10
    for h in hist:
        assert isinstance(h, dict)
        assert h['args'] == config_dict
    for method in (str, int, float):
        hist = history(entry_ids=method(hist_ids[0]))
        assert len(hist) == 1
    with pytest.raises(ValueError):
        hist = history(entry_ids='bla')
    hist = history(entry_ids='0')
    assert len(hist) == 0

def test_history_cmd(stdout, dummy_history, dummy_user):

    from evaluation_system.tests.mocks.dummy import DummyPlugin
    from evaluation_system.commands.history import Command
    from evaluation_system.tests import run_command_with_capture
    sys.stdout = stdout
    hist_ids = []
    uid = os.getuid()
    udata = pwd.getpwuid(uid)
    for i in range(10):
        hist_ids += [dummy_user.user.getUserDB().storeHistory(
            tool=DummyPlugin(),
            config_dict={'the_number': 42, 'number': 12, 'something': 'else', 'other': 'value', 'input': '/folder'},
            status=0,
            uid=udata.pw_name
        )]

    # test history output
    cmd = Command()
    output_str = run_command_with_capture(cmd, stdout, ['-d'])
    assert output_str.count('dummyplugin') == 10
    assert output_str.count('\n') == 10

    # test limit output
    output_str = run_command_with_capture(cmd, stdout, ['--limit=3'])
    assert output_str.count('dummyplugin') == 3
    assert output_str.count('\n') == 3

    # test no result
    output_str = run_command_with_capture(cmd, stdout, ['--plugin=blabla'])
    assert len(output_str) < 2


    # test return_command option
    output_str = run_command_with_capture(
            cmd, stdout, ['--entry_ids=%s' % hist_ids[0], '--return_command']
            )
    check_string = '--plugin dummyplugin something=\'else\' input=\'/folder\' other=\'value\' number=\'12\' the_number=\'42\''
    for string in check_string.split(' '):
        assert string.strip('\n').strip() in output_str
