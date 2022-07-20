"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import logging
from functools import partial
import os
import mock
from pathlib import Path
import pytest
import mock
import time
from subprocess import Popen
from evaluation_system.tests import run_cli, similar_string
from evaluation_system.misc.exceptions import PluginNotFoundError, ValidationError


@mock.patch("os.getpid", lambda: 12345)
def test_cli(dummy_plugin, capsys, dummy_config, caplog):

    from freva.cli.plugin import main as plugin_cli
    import time
    from evaluation_system.misc.exceptions import ValidationError
    from evaluation_system.misc import config

    with pytest.raises(ValidationError):
        plugin_cli(["dummyplugin"])
    plugin_cli(["dummyplugin", "the_number=13"])
    output = capsys.readouterr().out
    assert "the_number" in output
    assert "13" in output
    assert os.getpid() == 12345
    out_path = (
        Path(dummy_config.get("scheduler_output_dir"))
        / "dummyplugin"
        / "DummyPlugin-12345.local"
    )
    try:
        out_path.unlink()
    except FileNotFoundError:
        pass
    plugin_cli(["dummyplugin", "the_number=13"])
    interactive = capsys.readouterr().out
    assert dummy_plugin.plugin_output_file == out_path
    assert out_path.exists()
    with out_path.open() as f:
        assert interactive == f.read()
    out_path.unlink()
    plugin_cli(["dummyplugin", "the_number=13", "--batchmode"])
    output = capsys.readouterr().out
    _, loglevel, message = caplog.record_tuples[-1]
    assert loglevel == logging.INFO
    assert "tail -f" in message
    out_f = Path(message.split("\n")[-1].split(" ")[-1])
    assert out_f.exists()
    with out_f.open() as f:
        assert "pending" in f.read()


def test_killed_jobs_set_to_broken():
    from freva.cli.plugin import main as plugin_cli
    import freva

    cmd = ["freva-plugin", "dummyplugin", "the_number=13", "other=-10"]
    res = Popen(cmd)
    time.sleep(3)
    os.kill(res.pid, 15)
    time.sleep(2)
    hist = freva.history()[0]
    assert hist["status_dict"][hist["status"]].lower() == "broken"


@mock.patch("os.getpid", lambda: 12345)
def test_tool_doc(capsys, plugin_doc, admin_env, caplog):
    cmd = ["doc", "DummyPlugin", "--file-name", str(plugin_doc)]
    with mock.patch.dict(os.environ, admin_env, clear=True):
        run_cli(cmd)
        out = capsys.readouterr().out
        _, loglevel, message = caplog.record_tuples[-1]
        assert loglevel == logging.INFO
        assert "dummyplugin" in message.lower()
        assert "created" in message.lower()
        with pytest.raises(FileNotFoundError):
            run_cli(cmd[:-2])


@mock.patch("os.getpid", lambda: 12345)
def test_forbidden_tool_doc(dummy_env):
    from freva.cli.admin import update_tool_doc

    with pytest.raises(RuntimeError):
        update_tool_doc("dummyplugin")
    with pytest.raises(SystemExit):
        run_cli(["solr", "doc" "--help"])


@mock.patch("os.getpid", lambda: 12345)
def test_list_tools(capsys, dummy_env):
    from freva.cli.plugin import main as run

    run(["--list-tools"])
    plugin_list = capsys.readouterr().out
    assert "DummyPlugin" in plugin_list
    run_cli(["plugin", "dummyplugin", "--doc"])
    help_str = capsys.readouterr().out
    assert similar_string(
        help_str,
        """DummyPlugin (v0.0.0): A dummy plugin
Options:
number                  (default: <undefined>)
                        This is just a number, not really important
the_number              (default: <undefined>) [mandatory]
                        This is *THE* number. Please provide it
something               (default: test)
                        No help available.
other                   (default: 1.4)
                        No help available.
input                   (default: <undefined>)
                        An input file
variable                (default: tas)
                        An input variable
extra_scheduler_options (default: --qos=test, --array=20)
                        Set additional options for the job submission to the
                        workload manager (, seperated). Note: batchmode and web
                        only.""",
    )


@mock.patch("os.getpid", lambda: 12345)
def test_run_pyclientplugin(dummy_history):
    import freva
    from evaluation_system.misc import config
    from evaluation_system.model.plugins.models import ToolPullRequest

    res, _ = freva.run_plugin("dummyplugin", the_number=32, caption="Some caption")
    assert res == 0
    _, res = freva.run_plugin("dummyplugin", the_number=32, show_config=True)
    res = "\n".join([l.strip() for l in res.split("\n") if l.strip()])
    assert similar_string(
        res,
        """    number: -the_number: 32 something: test other: 1.4 input: -variable: tas
extra_scheduler_options: - (default: )""",
    )
    return_val, repo = freva.run_plugin("dummyplugin", repo_version=True)
    assert "repository" in repo.lower()
    assert "version" in repo.lower()

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


@mock.patch("os.getpid", lambda: 12345)
def test_run_plugin(capsys, dummy_history, dummy_env):
    from evaluation_system.misc import config

    with pytest.raises(ValidationError):
        run_cli(["plugin", "dummyplugin"])
    # test run tool
    run_cli(["plugin", "dummyplugin", "the_number=32", '--caption="Some caption"'])
    output_str = capsys.readouterr().out
    assert "Dummy tool was run" in output_str
    assert "the_number" in output_str
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
    for line in (
        "number: -",
        "the_number: 42",
        "something: test",
        "other: 1.4",
        "input: -",
    ):
        assert line in output_str


@mock.patch("os.getpid", lambda: 12345)
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
