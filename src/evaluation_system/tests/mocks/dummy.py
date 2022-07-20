import tempfile
import shutil
from pathlib import Path
from subprocess import run, PIPE
import os
import time

from evaluation_system.api.plugin import PluginAbstract
from evaluation_system.api.parameters import (
    ParameterDictionary,
    Integer,
    Float,
    String,
    InputDirectory,
)

from evaluation_system.model.user import User
from evaluation_system.model.db import UserDB


class DummyPlugin(PluginAbstract):
    """Stub class for implementing the abstract one"""

    __short_description__ = "A dummy plugin"
    __long_description__ = ""
    __version__ = (0, 0, 0)
    __tags__ = ["foo"]
    __category__ = "statistical"
    __name__ = "DummyPlugin"
    __parameters__ = ParameterDictionary(
        Integer(name="number", help="This is just a number, not really important"),
        Integer(
            name="the_number",
            mandatory=True,
            help="This is *THE* number. Please provide it",
        ),
        String(name="something", default="test"),
        Float(name="other", default=1.4),
        InputDirectory(name="input", help="An input file"),
        String(name="variable", default="tas", help="An input variable"),
    )
    _runs = []
    _template = "${number} - $something - $other"
    tool_developer = {"name": "DummyUser", "email": "data@dkrz.de"}

    def run_tool(self, config_dict=None):
        DummyPlugin._runs.append(config_dict)
        num = config_dict.get("other", 1.4)
        print(num)
        if num < 0:
            time.sleep(-num)
        tool_path = Path(__file__).parent / "plugin_env" / "bin" / "python"
        res = run(["which", "python"], stdout=PIPE, stderr=PIPE)
        assert "plugin_env" in os.environ["PATH"]
        out = res.stdout.decode().strip()
        assert out == str(tool_path.absolute())
        print(f"Dummy tool was run with: {config_dict}")
        return {
            "/tmp/dummyfile1": dict(type="plot"),
            "/tmp/dummyfile2": dict(type="data"),
        }


class DummyUser(User):
    """Create a dummy User object that allows testing"""

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._random_home:
            self.cleanRandomHome()
        return True

    def __init__(self, random_home=False, uid=None, **override):
        self._random_home = None
        self.username = override.get("pw_name", None)
        if random_home:
            if "pw_dir" in override:
                raise Exception("Can't define random_home and provide a home directory")
            override["pw_dir"] = tempfile.mkdtemp("_dummyUser")
            self._random_home = override["pw_dir"]
        super().__init__(uid=uid)

        class DummyUserData(list):
            """Override a normal list and make it work like the pwd read-only struct"""

            _NAMES = "pw_name pw_passwd pw_uid pw_gid pw_gecos pw_dir pw_shell".split()

            def __init__(self, arr_list):
                list.__init__(self, arr_list)

            def __getattribute__(self, name):
                # don't access any internal variable (avoid recursion!)
                if name[0] != "_" and name in self._NAMES:
                    return self[self._NAMES.index(name)]
                return list.__getattribute__(self, name)

        # copy the current data
        user_data = list(self._userdata[:])
        for key, value in override.items():
            user_data[DummyUserData._NAMES.index(key)] = value
        self._userdata = DummyUserData(user_data)
        self._db = UserDB(self)

    def cleanRandomHome(self):
        try:
            # make sure the home is a temporary one!!!
            shutil.rmtree(self._random_home)
        except (FileNotFoundError, OSError):
            pass
