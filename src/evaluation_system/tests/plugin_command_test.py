"""
Created on 18.05.2016

@author: Sebastian Illing
"""
from functools import partial
import os
import mock
import multiprocessing as mp
from pathlib import Path
import pytest
import time
from subprocess import Popen
from evaluation_system.tests import run_cli, similar_string
from evaluation_system.misc.exceptions import (
    PluginNotFoundError,
    ValidationError,
)


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
    assert "tail -f" in output
    out_f = Path([o.split()[-1] for o in output.split("\n") if "tail" in o][0])
    assert out_f.exists()
    with out_f.open() as f:
        assert "pending" in f.read()


def test_killed_jobs_set_to_broken():
    import freva

    proc = mp.Process(
        target=freva.run_plugin,
        args=("dummyplugin",),
        kwargs={"the_number": 10, "other": -10},
    )
    proc.start()
    time.sleep(1)
    proc.terminate()
    time.sleep(1)
    hist = freva.history()[0]
    assert hist["status_dict"][hist["status"]].lower() == "broken"


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

    res, _ = freva.run_plugin("dummyplugin", the_number=32, caption="Some caption")
    assert res == 0
    _, res = freva.run_plugin("dummyplugin", the_number=32, show_config=True)
    res = "\n".join([l.strip() for l in res.split("\n") if l.strip()])
    assert similar_string(
        res,
        """    number: -the_number: 32 something: test other: 1.4 input: -variable: tas
extra_scheduler_options: - (default: )""",
    )
    return_val, repo = freva.run_plugin("dummyplugin", the_number=32, repo_version=True)
    assert "repository" in repo.lower()
    assert "version" in repo.lower()

    with pytest.raises(PluginNotFoundError):
        freva.run_plugin("dummyplugin0")


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
