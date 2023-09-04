"""Additional utilities."""
import json
import logging
import os
import shlex
import subprocess
import time
from fnmatch import fnmatch
from functools import wraps
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, List, Literal, Optional, Tuple, Type, Union, cast

try:
    from IPython import get_ipython
except ImportError:  # pragma: no cover
    get_python = lambda: None  # pragma: no cover

import lazy_import
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

import freva
from evaluation_system.misc import logger
from evaluation_system.misc.utils import metadict as meta_type

pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
cancel_command = lazy_import.lazy_callable(
    "evaluation_system.api.workload_manager.cancel_command"
)
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
    """A class to interact with the status of a plugin application.

    With help of this class you can:

        - Check if a plugin is still running.
        - Get all results (data or plot files) of a plugin.
        - Check the configuration of a plugin.
        - Wait until the plugin is finished.

    Example
    -------

    The output of the ``freva.run_plugin`` method is an instance of the
    ``PluginStatus`` class. That means you can directly use the output of
    :py:meth:``freva.run_plugin`` to interact with the plugin status:

    .. execute_code::

        import freva
        res = freva.run_plugin("dummypluginfolders")
        print(res.status)

    You can also create an instance of the class yourself, if you know the
    ``history_id`` of a specific plugin run. Note that you can query these ids
    by making use of the :py:meth:``freva.history`` method:

    .. execute_code::

        import freva
        # Get the last run of the dummypluginfolders plugin
        hist = freva.history(plugin="dummypluginfolders", limit=1)[:-1]
        res = freva.PluginStatus(hist["id"])
        print(res.status)
    """

    def __init__(self, history_id: int) -> None:
        self._id: int = history_id

    def __repr__(self) -> str:
        return (
            f"PluginStatus('{self.plugin}', "
            f"config={str(self.configuration)}, status={self.status})"
        )

    @property
    def _hist(self) -> dict[str, Any]:
        log_level = logger.level
        logger.setLevel(logging.WARNING)
        try:
            hist = cast(
                list[dict[str, Any]],
                freva.history(entry_ids=self._id, return_results=True),
            )[0]
        except IndexError:
            logger.setLevel(log_level)
            return {}
        finally:
            logger.setLevel(log_level)
        hist["batch_settings"] = pm.get_batch_settings(self._id)
        return hist

    @property
    def status(self) -> str:
        """Get the state of the current plugin run."""
        hist = self._hist
        status_dict = hist.get("status_dict", {})
        status = hist.get("status")
        return cast(str, status_dict.get(status, "unkown"))

    @property
    def configuration(self) -> dict[str, Any]:
        """Get the plugin configuration."""
        return self._hist.get("configuration", {})

    @property
    def stdout(self) -> str:
        """Get the stdout of the plugin.

        Example
        -------
        Read the output of the plugin

        .. execute_code::

            import freva
            res = freva.run_plugin("dummypluginfolders")
            print(res.stdout)

        """
        try:
            return Path(self._hist["slurm_output"]).read_text(encoding="utf-8")
        except (FileNotFoundError, KeyError):
            return ""

    @property
    def batch_id(self) -> Optional[int]:
        """Get the id of the batch job, if the plugin was a batchmode job."""
        return self._hist.get("batch_settings", {}).get("job_id")

    @property
    def job_script(self) -> str:
        """Get the content of the job_script, if it was a batchmode job."""
        return self._hist.get("batch_settings", {}).get("job_script", "")

    def kill(self) -> None:
        """Kill a running batch job.

        This method has only affect on jobs there have been submitted using the
        ``batchmode=True`` flag.
        """
        if self.batch_id is not None:
            kill_cmd = cancel_command(
                self._hist["batch_settings"]["workload_manager"], self.batch_id
            )
            try:
                _ = subprocess.run(
                    shlex.split(kill_cmd),
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("Could not kill job with id %i", self.batch_id)

    @property
    def plugin(self) -> str:
        """Get the plugin name."""
        return self._hist.get("tool", "")

    def __str__(self) -> str:
        return json.dumps(self._hist, indent=3)

    @property
    def version(self) -> Tuple[int, int, int]:
        """Get the version of the plugin."""
        try:
            return cast(
                Tuple[int, int, int],
                tuple(
                    int(v.strip().strip("(").strip(")"))
                    for v in self._hist["version"].split(",")
                ),
            )
        except (KeyError, ValueError, TypeError):
            return (0, 0, 0)

    def wait(self, timeout: Union[float, int] = 28800) -> None:
        """Wait for a plugin to finish.

        This method will block until the plugin is running.

        Parameters
        ----------
        timeout: int, default: 28800
            Wait ``timeout`` seconds for the plugin to finish. If the plugin
            hasn't been finish raise a ValueError.

        Raises
        ------
        ValueError: If the plugin took longer than ``timeout`` seconds to finish

        Example
        -------

        This can be useful if a plugin was started using the ``batchmode=True``
        option and the execution of the code should wait until the plugin is
        finished.


        .. execute_code::

            import freva
            res = freva.run_plugin("dummypluginfolders", batchmode=True)
            res.wait(timeout=60) # Give the plugin 60 seconds to finish.

        """
        dt, n_itt = 0.5, 0
        max_itt = float(timeout) / dt
        text = "Waiting for plugin to finish... "
        spinner = Spinner("weather", text=text)
        with Live(spinner, refresh_per_second=3, console=Console(stderr=True)):
            while self.status in ("running", "scheduled", "unkown"):
                time.sleep(dt)
                n_itt += 1
                if n_itt > max_itt:
                    spinner.update(text=text + "ouch")
                    raise ValueError("Plugin did not finish")
            spinner.update(text=text + "ok")

    def get_result_paths(
        self,
        dtype: Literal["data", "plot"] = "data",
        glob_pattern: str = "*.nc",
    ) -> List[Path]:
        """Get all created paths of a certain data type.

        This method allows you to query all output files of the plugin run.
        You can either search for data files or plotted output.

        Parameters
        ----------
        dtype: str
            The data type of the returned paths. This should be either
            data or plot
        glob_pattern: str, default: *.nc
            Refine the output by filtering the returned files by the given
            glob pattern. By default only netCDF files ("*.nc") are added
            to the list.

        Returns
        -------
        List[Path]: A list of paths matching the search constrains.

        Example
        -------
        We are going to use a plugin called ``dummypluginfolders``
        which creates plots and netCDF files. In this example we want to
        open all netCDF files (``dtype = 'data'``) that match the filename
        constraint ``*data.nc``.


        .. execute_code::

            import freva
            import xarray as xr
            res = freva.run_plugin("dummypluginfolders", variable="pr")
            dset = xr.open_mfdataset(
                res.get_result_paths(dtype="data", glob_pattern="*data.nc")
            )
            print(dset.attrs["variable"])


        """
        return [
            Path(path)
            for (path, metadata) in self._hist.get("result", {}).items()
            if metadata.get("type") == dtype and fnmatch(path, glob_pattern)
        ]


class config:
    """Override the default or set the freva system configuration file.

    With the help of this class you can not only (temporarily) override
    the default configuration file and use a configuration from another
    project, but you can also set a path to a configuration file if no
    configuration file has been set.

    Parameters
    ----------
    config_file: str | pathlib.Path
        Path to the (new) configuration file.

    Examples
    --------
    Temporarily override the existing configuration file and use a new one.
    You can use a context manager to temporally use a different configuration
    and switch back later.

    ::

        import freva
        with freva.config("/work/freva/evaluation_system.conf"):
            freva.run_plugin("plugin_from_another_project")

    If you do not want to switch to another configuration only
    temporarily, but want to use it permanently, you can use
    :py:class:`freva.config` without a context manager:
    a context manager:

    ::

        import freva
        freva.config("/work/freva/evaluation_system.conf")
        files = sorted(freva.databrowser(project="user-1234", experiment="extremes"))

    """

    _original_config_env = os.environ.get(
        "EVALUATION_SYSTEM_CONFIG_FILE",
        cfg.CONFIG_FILE,
    )
    db_reloaded: List[bool] = [False]

    def __init__(self, config_file: Union[str, Path]) -> None:
        self._config_file = Path(config_file).expanduser().absolute()
        os.environ["EVALUATION_SYSTEM_CONFIG_FILE"] = str(self._config_file)
        cfg.reloadConfiguration(self._config_file)
        pm.reload_plugins()
        try:
            if django_settings.DATABASES:
                self.db_reloaded[0] = True
        except (ImproperlyConfigured, AttributeError):
            pass

    def __enter__(self) -> "config":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        os.environ["EVALUATION_SYSTEM_CONFIG_FILE"] = self._original_config_env
        cfg.reloadConfiguration(self._original_config_env)
        pm.reload_plugins()
        self.db_reloaded[0] = False
