"""Additional utilities."""
from functools import wraps
import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional, Union, Type, cast
from types import TracebackType

try:
    from IPython import get_ipython
except ImportError:  # pragma: no cover
    get_python = lambda: None  # pragma: no cover

from evaluation_system.misc.utils import metadict as meta_type
from evaluation_system.misc import logger
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


def handled_exception(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap the exception handler around a function."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that handles the exception."""
        try:
            return func(*args, **kwargs)
        except BaseException as error:
            exception_handler(error)
            raise  # Optionally re-raise the exception after handling

    return wrapper


def exception_handler(exception: BaseException, cli: bool = False) -> None:
    """Handle raising exceptions appropriately."""

    trace_back = exception.__traceback__
    appendix = {
        False: " - decrease log level via `freva.logger.setLevel`",
        True: " - increase verbosity flags (-v)",
    }[cli]
    append_msg = ""
    # Set only the last traceback of the exception
    if logger.level > logging.DEBUG and trace_back is not None:
        last_trace_back = trace_back
        while last_trace_back.tb_next:
            last_trace_back = last_trace_back.tb_next
        exception.__traceback__ = TracebackType(
            tb_next=None,
            tb_frame=last_trace_back.tb_frame,
            tb_lineno=last_trace_back.tb_lineno,
            tb_lasti=last_trace_back.tb_lasti,
        )
        append_msg = f"{appendix} for more information"
    msg = str(exception) + append_msg
    if cli:
        logger.exception(msg, exc_info=exception)
        raise SystemExit
    if logger.is_cli is False:
        logger.error(msg)
    if logger.level > logging.DEBUG:
        raise exception from None
    raise exception


class PluginStatus:
    """The state of a plugin application."""

    def __init__(self, metadict: Optional[meta_type], history_id: int) -> None:
        self._metadict = metadict
        self._id: int = history_id

    @property
    def _hist(self) -> dict[str, Any]:
        try:
            hist = cast(list[dict[str, Any]], history(entry_ids=self._id))[0]
        except IndexError as error:
            raise ValueError(f"Could not find entry {self.row_id}") from error
        return hist

    @property
    def status(self) -> str:
        """Get the state of the current plugin run."""
        hist = self._hist
        return cast(str, hist["status_dict"][hist["status"]])

    @property
    def configuration(self) -> dict[str, Any]:
        """Get the plugin configuration."""
        return self._hist["configuration"]

    @property
    def stdout(self) -> str:
        """Get the stdout of the plugin."""
        try:
            return Path(self._hist["slurm_output"]).read_text()
        except FileNotFoundError:
            return ""

    def get_result(self, dtype: str = "data") -> Optional[list[Path]]:
        """Get all created paths of a certain data type.

        Parameters
        ----------
        dtype: str
            The data type for the returned paths. This should be one
        """


class config:
    """Override the default or set the freva system configuration file.

    With help of this class you can not only (temporarily) override default
    config file and use a configuration from another project, you can also
    set a path to a configuration file in case no config file hasn't been set.

    Parameters
    ----------
    config_file: str | pathlib.Path
        Path to the (new) configuration file.

    Examples
    --------
    Temporarily Override the existing configuration file and use a new one.
    You can use a context manager to only temporally use another configuration
    and switch back afterwards.

    ::

        import freva
        with freva.config("/work/freva/evaluation_system.conf"):
            freva.run_plugin("plugin_from_another_project")

    If you do not want to only temporarily change to another configuration
    but constantly use it you can use the :py:class:`freva.config` without
    a context manager:

    ::

        import freva
        freva.config("/work/freva/evaluation_system.conf")
        files = sorted(freva.databrowser(project="user-1234", experiment="extremes"))

    """

    _original_config = os.environ.get(
        "EVALUATION_SYSTEM_CONFIG_FILE",
        cfg._DEFAULT_CONFIG_FILE_LOCATION,
    )

    def __init__(self, config_file: Union[str, Path]) -> None:
        self._config_file = Path(config_file).expanduser().absolute()
        os.environ["EVALUATION_SYSTEM_CONFIG_FILE"] = str(self._config_file)
        cfg.reloadConfiguration(self._config_file)
        pm.reload_plugins()

    def __enter__(self) -> "config":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        os.environ["EVALUATION_SYSTEM_CONFIG_FILE"] = self._original_config
        cfg.reloadConfiguration(self._original_config)
        pm.reload_plugins()
