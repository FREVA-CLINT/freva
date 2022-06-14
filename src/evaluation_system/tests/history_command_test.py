"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import os
import datetime
import pwd
import sys
import pytest


from evaluation_system.tests import run_cli
from evaluation_system.tests.mocks.dummy import DummyPlugin


def test_freva_history_method(dummy_history, dummy_user):
    from freva import history

    config_dict = {
        "the_number": 42,
        "number": 12,
        "something": "else",
        "other": "value",
        "input": "/folder",
        "variable": "pr",
    }
    hist_ids = []
    uid = os.getuid()
    udata = pwd.getpwuid(uid)
    for i in range(10):
        hist_ids += [
            dummy_user.user.getUserDB().storeHistory(
                tool=DummyPlugin(), config_dict=config_dict, status=0, uid=udata.pw_name
            )
        ]
    hist = history()
    assert isinstance(hist, (list, tuple))
    assert len(hist) == 10
    for h in hist:
        assert isinstance(h, dict)
        assert h["configuration"] == config_dict
    for method in (str, int, float):
        hist = history(entry_ids=method(hist_ids[0]))
        assert len(hist) == 1
    with pytest.raises(ValueError):
        hist = history(entry_ids="bla")
    hist = history(entry_ids="0")
    assert len(hist) == 0


def test_history_cmd(capsys, dummy_history, dummy_user):

    from freva.cli.history import main as run

    hist_ids = []
    uid = os.getuid()
    udata = pwd.getpwuid(uid)
    for i in range(10):
        hist_ids += [
            dummy_user.user.getUserDB().storeHistory(
                tool=DummyPlugin(),
                config_dict={
                    "the_number": 42,
                    "number": 12,
                    "something": "else",
                    "other": "value",
                    "input": "/folder",
                    "variable": "pr",
                },
                status=0,
                uid=udata.pw_name,
            )
        ]
    # test history output
    run(["-d"])
    output_str = capsys.readouterr().out
    assert output_str.count("dummyplugin") == 10
    assert output_str.count("\n") == 10
    # test limit output
    run_cli(["history", "--limit=3"])
    output_str = capsys.readouterr().out
    assert output_str.count("dummyplugin") == 3
    assert output_str.count("\n") == 3
    # test no result
    output_str = capsys.readouterr().out
    run_cli(["history", "--plugin", "blabla"])
    output_str = capsys.readouterr().out
    assert len(output_str) < 2
    # test return_command option
    run_cli(["history", f"--entry-ids={hist_ids[0]}", "--return-command"])
    output_str = capsys.readouterr().out.strip("\n").strip()
    check_string = [
        "plugin",
        "dummyplugin",
        "something=else",
        "input=/folder",
        "other=value",
        "number=12",
        "the_number=42",
        "variable=pr",
    ]
    for string in check_string:
        assert string in output_str
