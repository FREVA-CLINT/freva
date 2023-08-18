import logging
import os
import sys
from typing import Union

from rich.logging import RichHandler
from rich.console import Console

logger_stream_handle = RichHandler(
    rich_tracebacks=True,
    show_path=True,
    console=Console(soft_wrap=True, stderr=True),
)
logger_stream_handle.setLevel(logging.INFO)
logging.basicConfig(
    format="%(name)s - %(levelname)s - %(message)s",
    handlers=[logger_stream_handle],
    datefmt="[%X]",
    level=logging.INFO,
)


class FrevaLogger(logging.Logger):
    """Custom logger to assure that all log handles recieve the same level."""

    is_cli: bool = False
    """Indicate whether or not this logger belongs to a cli process."""

    def setLevel(self, level: Union[int, str]) -> None:
        super().setLevel(level)
        for handler in self.handlers:
            handler.setLevel(level)

    def set_level(self, level: Union[int, str]) -> None:
        """Set the log level of the logger."""
        self.setLevel(level)


logging.setLoggerClass(FrevaLogger)
logger: FrevaLogger = logging.getLogger("freva")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(logger_stream_handle)
_DEFAULT_CONFIG_FILE_LOCATION = os.path.join(
    sys.prefix, "freva", "evaluation_system.conf"
)
# now check if we have a configuration file, and read the defaults from there
CONFIG_FILE = os.environ.get(
    "EVALUATION_SYSTEM_CONFIG_FILE", _DEFAULT_CONFIG_FILE_LOCATION
)
