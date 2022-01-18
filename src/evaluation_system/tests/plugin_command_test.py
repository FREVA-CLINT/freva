"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import logging
from functools import partial
import os
from pathlib import Path
import pytest
import mock
import time
from evaluation_system.tests import run_cli, similar_string
from evaluation_system.misc.exceptions import PluginNotFoundError, ValidationError


def test_tool_doc(capsys, plugin_doc, admin_env, caplog):
    cmd = ["doc", "DummyPlugin", "--file-name", str(plugin_doc)]
    with mock.patch.dict(os.environ, admin_env, clear=True):
        run_cli(cmd)
        out = capsys.readouterr().out
        _, loglevel, message = caplog.record_tuples[-1]
        assert loglevel == logging.INFO
        assert 'dummyplugin' in message.lower()
        assert 'created' in message.lower()
        with pytest.raises(FileNotFoundError):
            run_cli(cmd[:-2])

def test_forbidden_tool_doc(dummy_env):
     from freva.cli.admin import update_tool_doc
     with pytest.raises(RuntimeError):
         update_tool_doc("dummyplugin")
     with pytest.raises(SystemExit):
         run_cli(["solr", "doc" "--help"])

def test_list_tools(capsys, dummy_env):
    from freva.cli.plugin import main as run
    with pytest.raises(PluginNotFoundError):
        run_cli("plugin --doc -d")
    run(["--list-tools"])
    plugin_list = capsys.readouterr().out
    assert "DummyPlugin" in plugin_list
    run_cli(["plugin", "dummyplugin", "--doc"])
    help_str = capsys.readouterr().out
    assert similar_string(
        help_str,
        """DummyPlugin (v0.0.0): A dummy plugin
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
       An input file.
""",
    )


def test_run_pyclientplugin(dummy_history):
    import freva
    from evaluation_system.misc import config
    from evaluation_system.model.plugins.models import ToolPullRequest
    res, _ =  freva.run_plugin(
            "dummyplugin",
            the_number=32,
            caption="Some caption"
    )
    assert res == 0
    _, res = freva.run_plugin("dummyplugin", the_number=32, show_config=True)
    res = "\n".join([l.strip() for l in res.split("\n") if l.strip()])
    assert similar_string(
        res, """    number: -the_number: 32 something: test other: 1.4 input: -"""
    )
    return_val, repo = freva.run_plugin("dummyplugin", repo_version=True)
    assert 'git' in repo
    ToolPullRequest.objects.all().delete()
    with pytest.raises(PluginNotFoundError):
       freva.run_plugin("dummyplugin0", pull_request=True, tag="")

    ret, _ = freva.run_plugin("dummyplugin", pull_request=True, tag="")
    assert ret != 0
    def pr_sleep(t, version=None, status=None, tool="dummyplugin"):
        t = ToolPullRequest.objects.get(tool=tool, tagged_version=version)
        t.status = status
        t.save()
    time.sleep = partial(pr_sleep, version="1.0", status="failed", tool="dummyplugin")
    retun_val, cmd_out = freva.run_plugin("dummyplugin", pull_request=True, tag="1.0")
    assert similar_string(
        cmd_out, """The pull request failed.\nPlease contact the admins.""", 0.7
    )
    time.sleep = partial(pr_sleep, version="2.0", status="success", tool="dummyplugin")
    _, cmd_out = freva.run_plugin("dummyplugin", pull_request=True, tag="2.0")
    assert similar_string(
        cmd_out,
        """dummyplugin plugin is now updated in the system. New version:  2.0""",
        0.7,
    )


def test_run_plugin(capsys, dummy_history, dummy_env):
    from evaluation_system.misc import config

    with pytest.raises(ValidationError):
        run_cli(["plugin", "dummyplugin"])
    # test run tool
    run_cli([
        "plugin", "dummyplugin", "the_number=32", '--caption="Some caption"'
    ])
    output_str = capsys.readouterr().out
    assert 'Dummy tool was run' in output_str
    assert 'the_number' in output_str
    # test get version
    run_cli(["plugin", "dummyplugin", "--repo-version"])
    # test batch mode
    run_cli(["plugin", "dummyplugin", "the_number=32", "--batchmode"])
    # test save config
    run_cli(["plugin", "dummyplugin", "the_number=32", "--save", "--debug"])
    fn = (
        Path(config.get(config.BASE_DIR_LOCATION))
        / "config/dummyplugin/dummyplugin.conf"
    )
    assert not fn.is_file()
    # test show config
    run_cli(["plugin", "dummyplugin", "the_number=42", "--show-config"])
    output_str = capsys.readouterr().out
    for line in ("number: -",
                 "the_number: 42",
                 "something: test",
                 "other: 1.4",
                 "input: -"):
        assert line in output_str


def test_handle_pull_request(dummy_env, capsys):
    from evaluation_system.model.plugins.models import ToolPullRequest

    ToolPullRequest.objects.all().delete()
    tool = "dummyplugin"
    run_cli(["plugin", tool, "--pull-request"])
    cmd_out = capsys.readouterr().out
    assert similar_string(cmd_out, """'Missing required option "--tag"'""", 0.7)
    def pr_sleep(t, version=None, status=None, tool="dummyplugin"):

        t = ToolPullRequest.objects.get(tool=tool, tagged_version=version)
        t.status = status
        t.save()

    time.sleep = partial(pr_sleep, version="1.0", status="failed", tool=tool)
    run_cli(["plugin", tool, "--pull-request", "--tag=1.0"])
    cmd_out = capsys.readouterr().out
    assert "The pull request failed.\nPlease contact the admins." in cmd_out
    time.sleep = partial(pr_sleep, version="2.0", status="success", tool=tool)
    run_cli(["plugin", tool, "--pull-request", "--tag=2.0"])
    cmd_out = capsys.readouterr().out
    assert "New version: 2.0" in cmd_out
