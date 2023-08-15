"""Additional utilities."""
import os
from pathlib import Path
from typing import Optional, Union, Type
from types import TracebackType

try:
    from IPython import get_ipython  # type: ignore
except ImportError:
    get_python = lambda: None

import lazy_import

pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
cfg = lazy_import.lazy_module("evaluation_system.misc.config")


def is_jupyter() -> bool:
    """Determine if we're running within an IPython kernel

    taken from: https://stackoverflow.com/questions/34091701/determine-if-were-in-an-ipython-notebook-session


    >>> is_jupyter()
    False
    """
    # check for `kernel` attribute on the IPython instance
    return getattr(get_ipython(), "kernel", None) is not None


class config:
    """Override the default evaluation system configuration file.

    With help of this class you can not only (temporarily) override default
    config file and use a configuration from another project, you can also
    set a path to a configuration file in case no config file wasn't set.

    Parameters
    ----------
    config_file: str | pathlib.Path
        Path to the new configuration file.

    Examples
    --------
    Temporally Override the existing configuration file and use a new one.
    You can use a context manager to only temporally use another configuration
    and switch back afterwards.

    ::
        import freva
        with config("/work/freva/evaluation_system.conf"):
            print(freva.list_plugins())

    """

    def __init__(self, config_file: Union[str, Path]) -> None:
        self._config_file = Path(config_file).expanduser().absolute()
        cfg.reloadConfiguration(self._config_file)
        pm.reload_plugins()

    def __enter__(self) -> "config":
        return self

    @property
    def _original_config(self) -> str:
        """Define the original configuration file path."""
        return os.environ.get(
            "EVALUATION_SYSTEM_CONFIG_FILE",
            cfg._DEFAULT_CONFIG_FILE_LOCATION,
        )

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        cfg.reloadConfiguration(self._original_config)
        pm.reload_plugins()
