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
    from evaluation_system.misc import config

    with pytest.raises(SystemExit):
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

    import re, freva

    pattern = r"'outputdir': '([^']*)'"

    plugin_cli(["dummypluginfolders", "variable=pr"])
    output_str = capsys.readouterr().out
    match = re.search(pattern, output_str)
    if match:
        folder_path = match.group(1)
    assert str(freva.history()[0]["id"]) in os.path.basename(
        os.path.normpath(folder_path)
    )

    plugin_cli(
        ["dummypluginfolders", "variable=pr", "--unique-output", "true"]
    )
    output_str = capsys.readouterr().out
    match = re.search(pattern, output_str)
    if match:
        folder_path = match.group(1)
    assert str(freva.history()[0]["id"]) in os.path.basename(
        os.path.normpath(folder_path)
    )

    plugin_cli(
        ["dummypluginfolders", "variable=pr", "--unique-output", "false"]
    )
    output_str = capsys.readouterr().out
    match = re.search(pattern, output_str)
    if match:
        folder_path = match.group(1)
    assert str(freva.history()[0]["id"]) not in os.path.basename(
        os.path.normpath(folder_path)
    )


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
    assert "number" in help_str
    assert "the_number" in help_str
    assert "Option" in help_str
    assert "Description" in help_str


@mock.patch("os.getpid", lambda: 12345)
def test_run_pyclientplugin(dummy_history):
    import freva
    from evaluation_system.misc import config

    res, _ = freva.run_plugin(
        "dummyplugin", the_number=32, caption="Some caption"
    )
    assert res == 0
    res = freva.plugin_info("dummyplugin", "config", the_number=32)
    res = "\n".join([l.strip() for l in res.split("\n") if l.strip()])
    assert "the_number" in res
    assert "input" in res
    repo = freva.plugin_info("dummyplugin", "repository", the_number=32)
    assert "repository" in repo.lower()
    assert "version" in repo.lower()
    with pytest.raises(ValueError):
        freva.plugin_info("dummyplugin", "repo")

    freva.logger.is_cli = False
    with pytest.raises(PluginNotFoundError):
        freva.run_plugin("dummyplugin0")


@mock.patch("os.getpid", lambda: 12345)
def test_run_plugin(capsys, dummy_history, dummy_env):
    from evaluation_system.misc import config

    with pytest.raises(SystemExit):
        run_cli(["plugin", "dummyplugin"])
    # test run tool
    run_cli(
        [
            "plugin",
            "dummyplugin",
            "the_number=32",
            '--caption="Some caption"',
            "--debug",
        ]
    )
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
        "number",
        "the_number",
        "something",
        "other",
        "input",
    ):
        assert line in output_str
