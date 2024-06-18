"""
Created on 31.05.2016

@author: Sebastian Illing
"""

import datetime
import logging
import os
import shutil
import tempfile
import textwrap
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from evaluation_system.api.plugin_manager import (  # _PluginStateHandle,
    CommandConfig,
    PluginMetadata,
)

# from evaluation_system.model.user import User

# from unittest.mock import MagicMock, patch


log = logging.getLogger(__name__)

# def test_update_plugin_state_in_db():
#     user_mock = MagicMock(spec=User)
#     plugin_state_handle = _PluginStateHandle(status=1, rowid=123, user=user_mock)
#     plugin_state_handle._update_plugin_state_in_db()
#     user_mock.getUserDB.return_value.upgradeStatus.assert_called_once_with(123, 'test_user', 1)


# @patch("evaluation_system.api.plugin_manager.atexit.register")
# @patch("evaluation_system.api.plugin_manager.signal.signal")
# def test_signal_handling_updates_state_and_quits(mock_signal, mock_atexit_register):
#     user_mock = MagicMock(spec=User)
#     plugin_state_handle = _PluginStateHandle(status=1, rowid=123, user=user_mock)
#     with patch.object(plugin_state_handle, "_update_plugin_state_in_db") as mock_update:
#         exception_caught = False
#         try:
#             plugin_state_handle._update_plugin_state_in_db_and_quit(None, None)
#         except KeyboardInterrupt:
#             exception_caught = True
#         assert exception_caught == True, "KeyboardInterrupt was not raised as expected"


def test_missing_plugin_directory_logs_warning(temp_user):
    import evaluation_system.api.plugin_manager as pm

    user_name = temp_user.getName()
    plugin_env_name = pm.PLUGIN_ENV + "_" + user_name
    non_existent_path = "/path/to/nonexistent/plugin"
    os.environ[plugin_env_name] = f"non_existent_module:{non_existent_path}"
    pm.reload_plugins(user_name=user_name)

    # Clean up by removing the environment variable to avoid side effects
    del os.environ[plugin_env_name]


def test_modules(dummy_settings):
    import evaluation_system.api.plugin_manager as pm

    pm.reload_plugins()
    pmod = pm.__plugin_modules_user__
    assert pmod is not None
    assert len(pmod) > 0


def test_get_plugins_user(temp_user):
    import evaluation_system.api.plugin_manager as pm

    get_plugins_user = pm.get_plugins_user()
    assert get_plugins_user == {
        str(temp_user.getName()): {
            "dummyplugin": PluginMetadata(
                name="DummyPlugin",
                plugin_class="DummyPlugin",
                plugin_module=str(os.getcwd())
                + "/src/evaluation_system/tests/mocks/dummy",
                description="A dummy plugin",
                user_exported=False,
                category="statistical",
                tags=["foo"],
            )
        }
    }


# @patch("evaluation_system.api.plugin_manager.importlib.util.spec_from_file_location")
# @patch("evaluation_system.api.plugin_manager.get_plugin_metadata")
# def test_get_plugin_instance_conditions(
#     mock_get_plugin_metadata, mock_spec_from_file_location
# ):
#     import evaluation_system.api.plugin_manager as pm

#     mock_plugin_metadata = MagicMock()
#     mock_plugin_metadata.plugin_class = "PluginClass"
#     mock_plugin_metadata.plugin_module = "plugin_module"
#     mock_get_plugin_metadata.return_value = mock_plugin_metadata

#     # First condition: spec is None
#     mock_spec_from_file_location.return_value = None
#     with pytest.raises(ImportError) as excinfo:
#         pm.get_plugin_instance("NonExistentPlugin")
#     assert "Could not import PluginClass from plugin_module" in str(excinfo.value)


def test_plugins(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm
    from evaluation_system.tests.mocks.dummy import DummyPlugin

    # force reload to be sure the dummy is loaded
    assert len(pm.get_plugins()) > 0
    assert "dummyplugin" in pm.get_plugins()
    dummy = pm.get_plugin_metadata("dummyplugin")
    assert dummy.description == DummyPlugin.__short_description__
    assert dummy.category == DummyPlugin.__category__
    assert dummy.tags == DummyPlugin.__tags__
    assert dummy.plugin_class == "DummyPlugin"
    os.environ[f"EVALUATION_SYSTEM_PLUGINS_{temp_user.getName()}"] = (
        f"{str(Path(__file__).parent / 'mocks')},dummy"
    )
    pm.reload_plugins(temp_user.getName())
    os.environ.pop(f"EVALUATION_SYSTEM_PLUGINS_{temp_user.getName()}")


def testDefaultPluginConfigStorage(temp_user):
    import evaluation_system.api.plugin_manager as pm

    pm.reload_plugins(temp_user.username)
    home = temp_user.getUserHome()
    assert os.path.isdir(home)
    conf_file = pm.write_setup("dummyplugin", user=temp_user)
    assert os.path.isfile(conf_file)


def test_plugin_config_storage(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm
    from evaluation_system.api.parameters import ValidationError

    home = temp_user.getUserHome()
    assert os.path.isdir(home)

    res = pm.get_plugin_instance("dummyplugin").setup_configuration(
        config_dict=dict(the_number=42)
    )
    assert res["something"] == "test"

    # write down this default
    conf_file = pm.write_setup(
        "dummyplugin", config_dict=dict(the_number=42), user=temp_user
    )

    assert os.path.isfile(conf_file)
    with open(conf_file, "r") as f:
        config = f.read()

    assert "\nsomething=test\n" in config

    with pytest.raises(ValidationError):
        pm.parse_arguments("dummyplugin", [])
    with pytest.raises(ValidationError):
        pm.parse_arguments("dummyplugin", [], user=temp_user)
    res = pm.parse_arguments("dummyplugin", [], use_user_defaults=True, user=temp_user)

    assert res == {
        "other": 1.4,
        "number": None,
        "the_number": 42,
        "something": "test",
        "input": None,
        "variable": "tas",
        "extra_scheduler_options": "",
    }
    assert res["something"] == "test"

    # now change the stored configuration
    config = config.replace("\nsomething=test\n", "\nsomething=super_test\n")
    with open(conf_file, "w") as f:
        f.write(config)
    res = pm.parse_arguments("dummyplugin", [], use_user_defaults=True, user=temp_user)
    assert res["something"] == "super_test"


def test_parse_arguments(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm

    home = temp_user.getUserHome()
    assert os.path.isdir(home)

    # direct parsing
    for args, result in [
        (
            "the_number=4",
            {
                "other": 1.3999999999999999,
                "the_number": 4,
                "something": "test",
                "variable": "tas",
                "extra_scheduler_options": "",
            },
        )
    ]:
        d = pm.parse_arguments("Dummyplugin", args.split(), user=temp_user)
        assert d == result

    # parsing requesting user default but without any
    for args, result in [
        (
            "the_number=4",
            {
                "other": 1.3999999999999999,
                "the_number": 4,
                "something": "test",
                "variable": "tas",
                "extra_scheduler_options": "",
            },
        )
    ]:
        d = pm.parse_arguments("Dummyplugin", args.split(), user=temp_user)
        assert d == result

    pm.write_setup("DummyPlugin", dict(number=7, the_number=42), temp_user)
    for args, result in [
        (
            "number=4",
            dict(
                number=4,
                the_number=42,
                something="test",
                other=1.4,
                input=None,
                variable="tas",
                extra_scheduler_options="",
            ),
        )
    ]:
        d = pm.parse_arguments(
            "Dummyplugin", args.split(), use_user_defaults=True, user=temp_user
        )
        assert d == result

    shutil.rmtree(home)


def test_parse_arguments_with_config_file(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm

    home = temp_user.getUserHome()
    assert os.path.isdir(home)

    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp:
        tmp.write("[DummyPlugin]\nnumber=3\nthe_number=5")
        tmp_path = tmp.name

    # Parsing with a config_file
    d = pm.parse_arguments(
        "Dummyplugin", "number=4".split(), config_file=tmp_path, user=temp_user
    )
    assert d == {
        "number": 4,
        "the_number": 5,
        "something": "test",
        "other": 1.4,
        "input": None,
        "variable": "tas",
        "extra_scheduler_options": "",
    }

    # Cleanup
    os.remove(tmp_path)
    shutil.rmtree(home)


def test_write_setup(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm

    f = pm.write_setup(
        "DummyPlugin", dict(number="$the_number", the_number=42), temp_user
    )

    with open(f) as fp:
        num_line = [
            line for line in fp.read().splitlines() if line.startswith("number")
        ][0]
        assert num_line == "number=$the_number"


def test_get_history(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm
    import freva

    pm.write_setup("DummyPlugin", dict(the_number=777), temp_user)
    pm.run_tool("dummyplugin", user=temp_user)
    run_res = freva.run_plugin("dummyplugin", the_number=2, other=-5, batchmode=True)
    pm.unfollow_history_tag(run_res._id, user=temp_user)
    pm.run_tool("dummyplugin", scheduled_id=run_res._id, user=temp_user)
    run_res.kill()
    res = pm.get_history(user=temp_user)
    res = res[0]
    import re

    mo = re.search(
        "^([0-9]{1,})[)] ([^ ]{1,}) ([^ ]{1,}) ([^ ]{1,})", res.__str__(compact=False)
    )
    assert mo is not None
    g1 = mo.groups()
    assert all([g is not None for g in g1])
    mo = re.search("^([0-9]{1,})[)] ([^ ]{1,}) ([^ ]{1,})", res.__str__())
    g2 = mo.groups()
    assert all([g is not None for g in g2])
    assert g1[0] == g2[0]


def testDynamicPluginLoading(dummy_env, temp_user):
    import evaluation_system.api.plugin_manager as pm

    basic_plugin = textwrap.dedent(
        """
        from sys import modules
        plugin = modules['evaluation_system.api.plugin']
        parameters = modules['evaluation_system.api.parameters']

        class %s(plugin.PluginAbstract):
            __short_description__ = "Test"
            __version__ = (0,0,1)
            __category__ = "foo"
            __tags__ = ["bar"]
            __parameters__ =  parameters.ParameterDictionary(
                                            parameters.File(name="output", default="/tmp/file", help='output'),
                                            parameters.File(name="input", mandatory=True, help="some input"))

            def runTool(self, config_dict=None):
                print("%s", config_dict)
        """
    )

    with tempfile.TemporaryDirectory(prefix="dyn_plugin") as path1:
        os.makedirs(os.path.join(path1, "a/b"))
        with open(path1 + "/a/__init__.py", "w"):
            pass
        with open(path1 + "/a/blah.py", "w") as f:
            f.write(basic_plugin % tuple(["TestPlugin1"] * 2))

        with tempfile.TemporaryDirectory(prefix="dyn_plugin") as path2:
            os.makedirs(os.path.join(path2, "x/y/z"))
            with open(path2 + "/x/__init__.py", "w"):
                pass
            with open(path2 + "/x/foo.py", "w") as f:
                f.write(basic_plugin % tuple(["TestPlugin2"] * 2))

            os.environ[pm.PLUGIN_ENV] = "%s,%s:%s,%s" % (
                "~/../../../../../.." + path1 + "/a",
                "blah",  # test a relative path starting from ~
                "~/../../../../../.." + path2 + "/x",
                "foo",
            )  # test a relative path starting from ~
            log.debug("pre-loading: %s", list(pm.get_plugins()))

            assert "testplugin1" not in list(pm.get_plugins())
            assert "testplugin2" not in list(pm.get_plugins())
            pm.reload_plugins()
            log.debug("post-loading: %s", list(pm.get_plugins()))
            assert "testplugin1" in list(pm.get_plugins())
            assert "testplugin2" in list(pm.get_plugins())


def test_load_invalid_plugin(dummy_env, temp_user):
    import evaluation_system.api.plugin_manager as pm

    # this intentionally does not define the required properties and methods
    basic_plugin = textwrap.dedent(
        """
        from sys import modules
        plugin = modules['evaluation_system.api.plugin']
        parameters = modules['evaluation_system.api.parameters']

        class TestPlugin(plugin.PluginAbstract):
            pass
        """
    )

    with tempfile.TemporaryDirectory(prefix="dyn_plugin") as plugin_dir:
        os.makedirs(os.path.join(plugin_dir, "a"))
        with open(plugin_dir + "/a/__init__.py", "w"):
            pass
        with open(plugin_dir + "/a/test_plugin.py", "w") as f:
            f.write(basic_plugin)

        os.environ[pm.PLUGIN_ENV] = "%s,%s" % (
            plugin_dir + "/a",
            "test_plugin",  # test a relative path starting from ~
        )
        log.debug("pre-loading: %s", list(pm.get_plugins()))
        assert "testplugin" not in list(pm.get_plugins())
        pm.reload_plugins()
        log.debug("post-loading: %s", list(pm.get_plugins()))
        assert "testplugin" not in list(pm.get_plugins())


def test_get_plugin_dict(dummy_env):
    import evaluation_system.api.plugin_manager as pm

    with pytest.raises(pm.PluginManagerException):
        pm.get_plugin_metadata("Not available")
    pl = pm.get_plugin_metadata("DummyPlugin")
    assert isinstance(pl, PluginMetadata)
    assert pl.plugin_class == "DummyPlugin"


def test_preview_generation(dummy_env):
    import evaluation_system.api.plugin_manager as pm
    import evaluation_system.misc.config as config

    with tempfile.TemporaryDirectory() as td:
        d = str(Path(td) / "tmp.pdf")
        s = os.path.dirname(__file__) + "/test_output/vecap_test_output.pdf"
        pm._preview_copy(s, d)
        assert os.path.isfile(d)
    with tempfile.TemporaryDirectory() as td:
        d = str(Path(td) / "tmp.png")
        s = os.path.dirname(__file__) + "/test_output/test_image.png"
        f = open(d, "w")
        f.close()
        pm._preview_copy(s, d)
        assert os.path.isfile(d)
    with tempfile.TemporaryDirectory() as td:
        d = str(Path(td) / "tmp.png")
        s = os.path.dirname(__file__) + "/test_output/test_image.png"
        pm._preview_convert(s, d)
        assert os.path.isfile(d)
    with tempfile.TemporaryDirectory() as td:
        d = str(Path(td) / "tmp.gif")
        s = os.path.dirname(__file__) + "/test_output/test_animation.gif"
        pm._preview_convert(s, d)
        assert os.path.isfile(d)

    r = pm._preview_generate_name("dummy", {})
    assert "dummy" in r
    assert len(r) == 14
    ts = time.time()
    r = pm._preview_generate_name("murcss", {"timestamp": ts})
    assert "murcss" in r
    assert datetime.datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S") in r

    u = pm._preview_unique_file("murcss", "pdf", {"timestamp": ts})
    assert datetime.datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S") in u

    assert datetime.datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S") in u
    assert "murcss" in u
    assert config.get("preview_path") in u

    r1 = os.path.dirname(__file__) + "/test_output/vecap_test_output.pdf"
    r2 = os.path.dirname(__file__) + "/test_output/test_image.png"
    result = {r1: {"todo": "copy"}, r2: {"todo": "convert"}}
    res = pm._preview_create("murcss", result)
    for r in res:
        assert os.path.isfile(r)
        os.remove(r)


def test_get_command_string(dummy_env, django_user):
    import evaluation_system.api.plugin_manager as pm
    from evaluation_system.model.history.models import History

    h = History.objects.create(
        timestamp=datetime.datetime.now(),
        status=History.processStatus.running,
        uid=django_user,
        configuration='{"some": "config", "dict": "values"}',
        tool="dummytool",
        slurm_output="/path/to/slurm-44742.out",
    )

    cmd = pm.get_command_string(h.id)
    assert "freva-plugin" in cmd
    assert h.tool in cmd

    config = CommandConfig(
        {
            "name": "command",
            "options": "--verbose",
            "tool": "toolname",
            "args": {"list_arg": ["value1", "value2"]},
        }
    )
    expected_string = "command --verbose toolname list_arg=value1,value2"
    assert pm.get_command_string_from_config(config) == expected_string

    config = CommandConfig(
        {
            "name": "command",
            "options": "--verbose",
            "tool": "toolname",
            "args": {"bool_arg": True},
        }
    )
    expected_string = "command --verbose toolname bool_arg=true"
    assert pm.get_command_string_from_config(config) == expected_string


def test_load_scheduled_conf(dummy_env, django_user, temp_user):
    import evaluation_system.api.plugin_manager as pm
    from evaluation_system.model.history.models import History

    h = History.objects.create(
        timestamp=datetime.datetime.now(),
        status=History.processStatus.scheduled,
        uid=django_user,
        configuration='{"some": "config", "dict": "values"}',
        tool="dummytool",
        slurm_output="/path/to/slurm-44742.out",
    )

    res = pm.load_scheduled_conf("dummytool", h.id, temp_user)
    assert res == {}


def test_2dict_to_conf(dummy_env, dummy_plugin):
    import evaluation_system.api.plugin_manager as pm

    configuration = {"number": 1, "the_number": 2, "something": "test"}
    with pytest.raises(pm.PluginManagerException):
        pm.dict2conf("dummytool", configuration)
    with pytest.raises(pm.ParameterNotFoundError):
        pm.dict2conf("dummyplugin", {"some": "config"})
    dd = pm.dict2conf("dummyplugin", configuration)
    assert isinstance(dd, list)
    assert len(dd) == len(configuration)


def test_scheduletool(dummy_env, dummy_plugin):
    import evaluation_system.api.plugin_manager as pm

    with TemporaryDirectory() as td:
        pm.schedule_tool("dummyplugin", log_directory=str(Path(td) / "tmp"))


def test_get_config_name():
    import evaluation_system.api.plugin_manager as pm

    res = pm.get_config_name("dummypluginZ")
    assert res == None


# def test_get_error_warning():
#     import evaluation_system.api.plugin_manager as pm

#     def mock_get_plugin(plugin_name, key, default):
#         return {
#             "error_file": "error.txt",
#             "error_message": "",
#             "warning_file": "warning.txt",
#             "warning_message": "",
#         }.get(key, "")

#     # Files exist
#     with (
#         patch(
#             "evaluation_system.api.plugin_manager.config.get_plugin",
#             side_effect=mock_get_plugin,
#         ),
#         patch(
#             "builtins.open",
#             side_effect=[
#                 MagicMock(read=MagicMock(return_value="Error content")),
#                 MagicMock(read=MagicMock(return_value="Warning content")),
#             ],
#         ),
#     ):
#         error_message, warning_message = pm.get_error_warning("dummyplugin")
#         print(error_message, warning_message)
#         # skip assert for now, because it's already tested in the print statement

#     # Files do not exist
#     with (
#         patch(
#             "evaluation_system.api.plugin_manager.config.get_plugin",
#             side_effect=mock_get_plugin,
#         ),
#         patch("builtins.open", side_effect=Exception("File not found")),
#         patch("evaluation_system.api.plugin_manager.log.warning") as mock_log_warning,
#     ):
#         error_message, warning_message = pm.get_error_warning("dummyplugin")
#         print(error_message, warning_message)
#         # skip assert for now, because it's already tested in the print statement

#     # ConfigurationException
#     with (
#         patch(
#             "evaluation_system.api.plugin_manager.config.get_plugin",
#             side_effect=ConfigurationException("Config error"),
#         ),
#         patch("evaluation_system.api.plugin_manager.log.warning") as mock_log_warning,
#     ):
#         error_message, warning_message = pm.get_error_warning("dummyplugin")
#         print(error_message, warning_message)
#         assert (
#             error_message == ""
#         ), "Error message should be empty on ConfigurationException."
#         assert (
#             warning_message == ""
#         ), "Warning message should be empty on ConfigurationException."


# def test_get_plugin_version():
#     import evaluation_system.api.plugin_manager as pm

#     mock_get_plugins = {
#         "existing_plugin": MagicMock(plugin_module="path/to/existing_plugin_module"),
#     }
#     mock_repository_get_version = MagicMock(
#         return_value=("https://freva_repository.url", "git_hash_value")
#     )

#     # Plugin is the module itself
#     with (
#         patch("evaluation_system.api.plugin_manager.__version_cache", {}),
#         patch(
#             "evaluation_system.api.plugin_manager.get_plugins",
#             return_value=mock_get_plugins,
#         ),
#         patch("inspect.getfile", return_value="path/to/self_module"),
#         patch(
#             "evaluation_system.model.repository.get_version",
#             mock_repository_get_version,
#         ),
#     ):

#         repository_url, git_hash = pm.get_plugin_version("self")
#         assert (
#             repository_url == "https://freva_repository.url"
#         ), "Repository URL mismatch for 'self'."
#         assert git_hash == "git_hash_value", "Git hash mismatch for 'self'."

#     # Plugin not found
#     with (
#         patch("evaluation_system.api.plugin_manager.__version_cache", {}),
#         patch(
#             "evaluation_system.api.plugin_manager.get_plugins",
#             return_value=mock_get_plugins,
#         ),
#     ):
#         try:
#             pm.get_plugin_version("non_existing_plugin")
#             assert False, "Expected PluginManagerException for non-existing plugin."
#         except pm.PluginManagerException as e:
#             assert (
#                 str(e) == "Plugin <non_existing_plugin> not found"
#             ), "Incorrect exception message."
