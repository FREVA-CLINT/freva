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
    Directory,
)

from evaluation_system.model.user import User
from evaluation_system.model.db import UserDB


class DummyPluginFolders(PluginAbstract):
    """Stub class for implementing the abstract one"""

    __short_description__ = "A dummy plugin with outputdir folder"
    __long_description__ = ""
    __version__ = (0, 0, 0)
    __tags__ = ["foo"]
    __category__ = "statistical"
    __name__ = "DummyPluginFolders"
    __parameters__ = ParameterDictionary(
        String(name="variable", default="tas", help="An input variable"),
        Directory(
            name="outputdir",
            default="$USER_OUTPUT_DIR/$SYSTEM_DATETIME",
            mandatory=False,
            help="The default output directory",
        ),
    )
    _runs = []
    _template = "${number} - $something - $other"
    tool_developer = {"name": "DummyUser", "email": "data@dkrz.de"}

    def run_tool(self, config_dict=None):
        DummyPluginFolders._runs.append(config_dict)
        tool_path = Path(__file__).parent / "plugin_env" / "bin" / "python"
        res = run(["which", "python"], stdout=PIPE, stderr=PIPE)
        assert "plugin_env" in os.environ["PATH"]
        print(f"DummyPluginFolders tool was run with: {config_dict}")
        return {
            "/tmp/dummyfile1": dict(type="plot"),
            "/tmp/dummyfile2": dict(type="data"),
        }
