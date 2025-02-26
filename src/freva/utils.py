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
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

try:
    from IPython import get_ipython
except ImportError:  # pragma: no cover
    get_ipython = lambda: None  # pragma: no cover

import lazy_import
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import OperationalError
from evaluation_system.misc import logger
from evaluation_system.misc.exceptions import ConfigurationException
from evaluation_system.misc.utils import metadict as meta_type
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

import freva

pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
cancel_command = lazy_import.lazy_callable(
    "evaluation_system.api.workload_manager.cancel_command"
)
cfg = lazy_import.lazy_module("evaluation_system.misc.config")
db_settings = lazy_import.lazy_module("evaluation_system.settings.database")


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
        wrong_config_msg = {
            False: (
                "consult the `freva.config` class to see how to pass a "
                "valid configuration."
            ),
            True: (
                "export the EVALUATION_SYSTEM_CONFIG_FILE "
                "environment variable to set a valid configuration file."
            ),
        }
        try:
            return func(*args, **kwargs)
        except (ImproperlyConfigured, OperationalError):  # prgama: no cover
            # Wrap django error in a more informative exception
            msg = "Your freva instance doesn't seem to be properly configured: "
            raise ConfigurationException(
                msg + wrong_config_msg[logger.is_cli]
            ) from None
        except BaseException as error:
            exception_handler(error)

    return wrapper


def exception_handler(exception: BaseException, cli: bool = False) -> None:
    """Handle raising exceptions appropriately."""

    trace_back = exception.__traceback__
    appendix = {
        False: " - decrease log level via `freva.logger.setLevel(10)`",
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
    def _hist(self) -> Dict[str, Any]:
        log_level = logger.level
        logger.setLevel(logging.WARNING)
        try:
            hist = cast(
                List[Dict[str, Any]],
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
    def history_id(self) -> int:
        """Get the ID of this plugin run in the freva history."""
        return self._id

    @property
    def status(self) -> str:
        """Get the state of the current plugin run."""
        hist = self._hist
        status_dict = hist.get("status_dict", {})
        status = hist.get("status")
        return cast(str, status_dict.get(status, "unknown"))

    @property
    def configuration(self) -> Dict[str, Any]:
        """Get the plugin configuration."""
        return self._hist.get("configuration", {})

    @property
    def stdout(self) -> str:
        """Get the stdout of the plugin.

        Example
        -------
        Read the output of the plugin:

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
        ValueError: If the plugin took longer than ``timeout`` seconds to finish.

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
            while self.status in ("running", "scheduled", "unknown"):
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
            data or plot.
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
    configuration file has been set. Additionally you can set any plugin
    paths that are not part of the configuration file.

    Parameters
    ----------
    config_file: str | pathlib.Path, default: None
        Path to the (new) configuration file.
    plugin_path: str | List[str], default: None
        New plugins that should be used, use a list of paths if you want
        export multiple plugins.

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

    Import a new user defined plugin, for example if you have created a plugin
    called ``MyPlugin`` that is located in ``~/freva/myplugin/plugin.py``
    you would set to ``plugin_path='~/freva/my_plugin,plugin_module'``.

    ::

        import freva
        freva.config(plugin_path="~/freva/my_plugin,plugin_module")
        freva.run_plugin('MyPlugin", variable1=1, variable2="a")

    In the same fashion you can set multiple plugin paths:

    ::
        import freva
        freva.config(plugin_path=["~/freva/my_plugin1,plugin_module_b"],
                                  "~/ freva/my_plugin2,plugin_module_b"])

    """

    _original_config_env = os.environ.get(
        "EVALUATION_SYSTEM_CONFIG_FILE",
    )
    _original_plugin_env = os.environ.get("EVALUATION_SYSTEM_PLUGINS")
    db_reloaded: List[bool] = [False]

    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        plugin_path: Optional[Union[str, List[str]]] = None,
    ) -> None:
        plugin_path = plugin_path or []
        if isinstance(plugin_path, str):
            plugin_path = [plugin_path]
        if config_file:
            config_file = Path(config_file).expanduser().absolute()
            os.environ["EVALUATION_SYSTEM_CONFIG_FILE"] = str(config_file)
        try:
            if django_settings.DATABASES:
                self.db_reloaded[0] = True
            db_settings.reconfigure_django(config_file)
        except (ImproperlyConfigured, AttributeError):  # prgama: no cover
            pass  # prgama: no cover
        assert isinstance(db_settings.SETTINGS, dict)
        if plugin_path or config_file:
            pm.reload_plugins(plugin_path=plugin_path)

    def __enter__(self) -> "config":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        os.environ.pop("EVALUATION_SYSTEM_CONFIG_FILE")
        if self._original_config_env:
            os.environ["EVALUATION_SYSTEM_CONFIG_FILE"] = self._original_config_env
        db_settings.reconfigure_django(self._original_config_env)
        try:
            pm.reload_plugins()
        except Exception:
            pass
        self.db_reloaded[0] = False
