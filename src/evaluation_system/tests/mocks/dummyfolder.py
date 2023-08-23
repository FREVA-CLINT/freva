import os
import shutil
import tempfile
import time
from pathlib import Path
from subprocess import PIPE, run

from netCDF4 import Dataset as nc
from PIL import Image

from evaluation_system.api.parameters import (
    Directory,
    Float,
    InputDirectory,
    Integer,
    ParameterDictionary,
    String,
)
from evaluation_system.api.plugin import PluginAbstract
from evaluation_system.model.db import UserDB
from evaluation_system.model.user import User


class DummyPluginFolders(PluginAbstract):
    """Stub class for implementing the abstract one"""

    __short_description__ = "A dummy plugin with outputdir folder"
    __long_description__ = ""
    __tags__ = ["foo"]
    __version__ = ("foo", "bar")
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
        out_dir = Path(config_dict["outputdir"]).absolute().expanduser()
        out_dir.mkdir(exist_ok=True, parents=True)
        image = Image.new("RGB", (300, 200), "white")
        image.save(str(out_dir / "plot.png"))
        with nc(str(out_dir / "data.nc"), "w") as dataset:
            dataset.variable = config_dict["variable"]
        print(f"Processing output in {config_dict['outputdir']}")
        return self.prepare_output(config_dict["outputdir"])
