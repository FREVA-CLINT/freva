import logging
import os
import sys
from typing import Optional, Union, cast

from rich.console import Console
from rich.logging import RichHandler

logger_stream_handle = RichHandler(
    rich_tracebacks=True,
    show_path=False,
    console=Console(soft_wrap=False, stderr=True),
)
logger_stream_handle.setLevel(logging.INFO)
logging.basicConfig(
    format="%(name)s - %(levelname)s - %(message)s",
    handlers=[logger_stream_handle],
    datefmt="[%X]",
    level=logging.INFO,
)


class FrevaLogger(logging.Logger):
    """Custom logger to assure that all log handles receive the same level."""

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
logger: FrevaLogger = cast(FrevaLogger, logging.getLogger("freva"))
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(logger_stream_handle)


class _ConfigWrapper:
    """Convenience class that helps to dynamically set the location of the
    evaluation system config file."""

    _env: str = "EVALUATION_SYSTEM_CONFIG_FILE"

    def __init__(
        self,
        default_file: str,
    ):
        self.default_file = default_file

    def __fspath__(self) -> str:
        return os.environ.get(self._env, self.default_file)

    def __repr__(self) -> str:
        return self.__fspath__()
