"""
Created on 17.5.2016

@author: Sebastian Illing
"""
import subprocess
import os
from pathlib import Path
import tempfile
import shutil

import pytest

DUMMY_USER = {"pw_name": "someone"}


def test_dummy_user(temp_user, dummy_settings, dummy_env):
    """Be sure the dummy user is created as expected"""
    dummy_name = "non-existing name"
    from evaluation_system.model.user import User
    from evaluation_system.tests.mocks.dummy import DummyUser

    with pytest.raises(Exception):
        DummyUser(random_home=True, pw_dir="anything")

    with DummyUser(random_home=True, pw_name=dummy_name) as d_user:
        # populate the test directory as required
        d_user.prepareDir()
        assert dummy_name == d_user.getName()
        cfg_file = os.path.join(d_user.getUserBaseDir(), User.EVAL_SYS_CONFIG)

        # check configuration file writing
        assert not os.path.isfile(cfg_file)
        cnfg = d_user.getUserConfig()
        cnfg.add_section("test_section")
        cnfg.set("test_section", "some_key", "a text value\nwith many\nlines!")
        d_user.writeConfig()
        assert os.path.isfile(cfg_file)
        # check configuration file reading
        with open(cfg_file, "w") as fp:
            ##Note multi line values in the configuration file need to be indented...
            fp.write(
                "[test2]\nkey1 = 42\nkey2=Some\n\tmany\n\tlines=2\nkey3=%(key1)s0\n"
            )
        cnfg = d_user.reloadConfig()
        assert cnfg.getint("test2", "key1") == 42
        # ...but the indentation disappears when returned directly
        assert cnfg.get("test2", "key2") == "Some\nmany\nlines=2"
        assert cnfg.getint("test2", "key3") == 420


def test_getters(dummy_settings, dummy_env):
    """Test the object creation and some basic return functions"""
    from evaluation_system.model.user import User
    from evaluation_system.misc import config
    from evaluation_system.tests.mocks.dummy import DummyUser

    try:
        config._config[config.DIRECTORY_STRUCTURE_TYPE] = "local"
        with DummyUser(random_home=True, pw_name="someone") as temp_user:
            assert DUMMY_USER["pw_name"] == temp_user.getName()
            assert temp_user.getUserHome().startswith(tempfile.gettempdir())
            assert os.getuid() == temp_user.getUserID()
            print(config.get("directory_structure_type"))
            db = temp_user.getUserDB()
            assert db is not None
            baseDir = "/".join([temp_user.getUserHome(), config.get(config.BASE_DIR)])
            assert baseDir == temp_user.getUserBaseDir()
            tool1_cnfDir = os.path.join(baseDir, User.CONFIG_DIR, "tool1")
            tool1_chDir = os.path.join(baseDir, User.CACHE_DIR, "tool1")
            tool1_outDir = os.path.join(baseDir, User.OUTPUT_DIR, "tool1")
            tool1_plotDir = os.path.join(baseDir, User.PLOTS_DIR, "tool1")
            assert temp_user.getUserScratch() == "/tmp/scratch/%s" % temp_user.getName()
            # check we get the configuration directory of the given tool
            assert tool1_cnfDir == temp_user.getUserConfigDir("tool1")
            assert tool1_chDir == temp_user.getUserCacheDir("tool1")
            assert tool1_outDir == temp_user.getUserOutputDir("tool1")
            assert tool1_plotDir == temp_user.getUserPlotsDir("tool1")
            # check we get the general directory of the tools (should be the parent of the previous one)
            assert os.path.dirname(tool1_cnfDir) == temp_user.getUserConfigDir()
            assert os.path.dirname(tool1_chDir) == temp_user.getUserCacheDir()
            assert os.path.dirname(tool1_outDir) == temp_user.getUserOutputDir()
            assert os.path.dirname(tool1_plotDir) == temp_user.getUserPlotsDir()
    finally:
        config.reloadConfiguration()


def test_directory_creation(temp_user, dummy_env):
    """
    This tests assures we always know what is being created
    in the framework directory
    """
    from evaluation_system.tests.mocks.dummy import DummyUser

    # assure we have a temp directory as HOME for testing
    testUserDir = tempfile.mkdtemp("_es_userdir")
    with DummyUser(pw_dir=testUserDir) as testUser:
        # assure we have a home directory setup
        assert os.path.isdir(testUser.getUserHome())
        baseDir = testUser.getUserBaseDir()
        # check home is completely created
        # self.assertFalse(os.path.isdir(baseDir)) Basic dir structure is created when running a tool because of
        # history, so this doesn't apply anymore
        testUser.prepareDir()
        assert os.path.isdir(baseDir)
        created_dirs = [
            testUser.getUserConfigDir(),
            testUser.getUserCacheDir(),
            testUser.getUserOutputDir(),
            testUser.getUserPlotsDir(),
        ]
        for directory in created_dirs:
            assert os.path.isdir(directory)


def test_directory_creation2(temp_user, dummy_env):
    try:

        testUser = temp_user
        # assure we have a home directory setup
        assert os.path.isdir(testUser.getUserHome())
        dir1 = temp_user.getUserConfigDir("test_tool", create=False)
        assert not os.path.isdir(dir1)
        dir2 = temp_user.getUserConfigDir("test_tool", create=True)
        assert dir1 == dir2
        assert os.path.isdir(dir1)
    finally:
        shutil.rmtree(Path(temp_user.getUserBaseDir()).parent)


def test_central_directory_Creation(temp_dir, dummy_settings, dummy_env):
    from evaluation_system.tests.mocks.dummy import DummyUser
    from evaluation_system.misc import config

    try:
        config._config[config.BASE_DIR_LOCATION] = str(temp_dir)
        config._config[
            config.DIRECTORY_STRUCTURE_TYPE
        ] = config.DIRECTORY_STRUCTURE.CENTRAL
        with DummyUser(random_home=False, **DUMMY_USER) as temp_user:
            dir1 = temp_user.getUserBaseDir()
            assert dir1 == os.path.join(
                config.get(config.BASE_DIR_LOCATION),
                config.get(config.BASE_DIR),
                str(temp_user.getName()),
            )
            dir2 = temp_user.getUserOutputDir("sometool")
            assert dir2 == os.path.join(
                config.get(config.BASE_DIR_LOCATION),
                config.get(config.BASE_DIR),
                str(temp_user.getName()),
                User.OUTPUT_DIR,
                "sometool",
            )
    finally:
        config.reloadConfiguration()
        # if os.path.isdir(temp_dir) and temp_dir.startswith(tempfile.gettempdir()):
        #    #make sure the home is a temporary one!!!
        #    shutil.rmtree(temp_dir)


def test_config_file(temp_user, dummy_settings):
    tool = "test_tool"
    assert temp_user.getUserConfigDir(
        tool
    ) + "/%s.conf" % tool == temp_user.getUserToolConfig(tool)
