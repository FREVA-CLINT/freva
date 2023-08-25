"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import json
import multiprocessing as mp
import os
import time
from functools import partial
from pathlib import Path
from subprocess import Popen

import mock
import pytest

from evaluation_system.misc.exceptions import PluginNotFoundError, ValidationError
from evaluation_system.tests import run_cli, similar_string


def test_cli(dummy_plugin, capsys, dummy_config, caplog):
    with mock.patch("os.getpid", lambda: 12345):
        from evaluation_system.misc import config
        from freva.cli.plugin import main as plugin_cli

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

        import freva

        plugin_cli(["dummypluginfolders", "variable=pr"])
        folder_path = capsys.readouterr().out.strip().split()[-1]
        assert str(freva.history()[0]["id"]) in os.path.basename(
            os.path.normpath(folder_path)
        )

        plugin_cli(["dummypluginfolders", "variable=pr", "--unique-output", "true"])
        folder_path = capsys.readouterr().out.strip().split()[-1]
        assert str(freva.history()[0]["id"]) in os.path.basename(
            os.path.normpath(folder_path)
        )

        plugin_cli(["dummypluginfolders", "variable=pr", "--unique-output", "false"])
        folder_path = capsys.readouterr().out.strip().split()[-1]
        assert str(freva.history()[0]["id"]) not in os.path.basename(
            os.path.normpath(folder_path)
        )


def test_killed_jobs_set_to_broken(dummy_config):
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


def test_run_pyclientplugin(dummy_history):
    import freva
    from evaluation_system.misc import config

    res = freva.run_plugin("dummyplugin", the_number=32, caption="Some caption")
    assert res.status == "finished"
    assert len(res.version) == 3
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


def test_plugin_status(dummy_env, caplog) -> None:
    """Test the plugin status quries."""
    import os

    import freva

    res = freva.run_plugin("dummyplugin", the_number=2, other=-5, batchmode=True)
    with pytest.raises(ValueError):
        res.wait(2)
    assert res.status == "running"
    res.kill()
    time.sleep(0.5)
    assert res.status == "broken"
    res.kill()
    res = freva.run_plugin("dummyplugin", the_number=2, other=-1, batchmode=True)
    res.wait()
    assert res.status == "finished"
    assert isinstance(res.batch_id, int)


def test_plugin_output(dummy_history) -> None:
    """Test the output of the plugin."""
    import freva

    res = freva.run_plugin("dummypluginfolders", variable="pr", caption="Some caption")
    assert res.status == "finished"
    assert isinstance(res.get_result_paths(), list)
    assert len(res.get_result_paths()) > 0
    assert "variable" in res.configuration
    assert res.configuration["variable"] == "pr"
    assert len(res.stdout) > 1
    assert res.plugin.lower() == "dummypluginfolders"
    assert len(res.version) == 3
    assert "pr" in res.__repr__()
    assert "finished" in res.__repr__()
    assert "dummypluginfolders" in res.__repr__()
    assert res.job_script == ""
    assert res.batch_id is None


def test_empty_status(dummy_history, capsys) -> None:
    """Test the plugin status quries."""
    import freva

    res = freva.PluginStatus(12345)
    assert res.status == "unkown"
    assert res.configuration == {}
    assert res.stdout == ""
    assert res.batch_id is None
    assert res.job_script == ""
    res.kill()
    assert res.plugin == ""
    assert res.version == (0, 0, 0)
    assert res.get_result_paths() == []


def test_run_plugin(capsys, dummy_history, dummy_env):
    import freva
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
    output_str = capsys.readouterr().out
    # test batch mode
    run_cli(["plugin", "dummypluginfolders", "--json"])
    output = json.loads(capsys.readouterr().out)
    assert isinstance(output, dict)
    assert "result" in output
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
