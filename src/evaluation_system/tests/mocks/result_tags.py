from evaluation_system.api import parameters
from evaluation_system.api.plugin import PluginAbstract
from evaluation_system.api.parameters import (
    ParameterDictionary,
    Integer,
    Float,
    String,
    Directory,
)


class ResultTagTest(PluginAbstract):
    """
    This Plugin tests the functionality of the resulttags
    """

    __parameters__ = parameters.ParameterDictionary(
        parameters.File(name="input", mandatory=True)
    )
    __short_description__ = "Test tool inserting results"
    __category__ = ""
    __tags__ = ["foo"]
    __version__ = (0, 0, 2)

    def run_tool(self, config_dict=None):
        folder = config_dict.get("folder", None)
        if folder:
            output = folder
        else:
            output = {config_dict["input"]: {"caption": "Manually added result"}}
        return self.prepare_output(output)
