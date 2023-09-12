"""Additional utilities."""
import json
import logging
import os
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from fnmatch import fnmatch
from functools import wraps
from getpass import getuser
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
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

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
import lazy_import
import nbclient
import nbformat
import requests
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

import freva
from evaluation_system.misc import logger
from evaluation_system.misc.exceptions import ConfigurationException

pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
cancel_command = lazy_import.lazy_callable(
    "evaluation_system.api.workload_manager.cancel_command"
)
get_solr_time_range = lazy_import.lazy_callable(
    "evaluation_system.misc.utils.get_solr_time_range"
)
cfg = lazy_import.lazy_module("evaluation_system.misc.config")
futures = lazy_import.lazy_module("evaluation_system.model.futures")


@contextmanager
def get_spinner(
    text: str,
    spinner_type: str = "weather",
    clear: bool = False,
    refresh_rate: int = 3,
) -> Iterator[Spinner]:
    """Create a spinner giving a visual feedback on computational tasks."""

    spinner = Spinner(spinner_type, text=f"{text} ...")
    console = Console(stderr=True)
    with Live(spinner, refresh_per_second=refresh_rate, console=console):
        yield spinner
        spinner.update(text=str(spinner.text) + " ok")
        if clear:
            spinner.update(text="")
            console.clear_live()


def is_jupyter() -> bool:
    """Determine if we're running within an IPython kernel

    taken from: https://stackoverflow.com/questions/34091701/determine-if-were-in-an-ipython-notebook-session


    >>> is_jupyter()
    False
    """
    # check for `kernel` attribute on the IPython instance
    return getattr(get_ipython(), "kernel", None) is not None


def copy_doc_from(
    func: Callable[..., Any]
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to copy a doc string from a function to the wrapped func."""

    def decorator(target: Callable[..., Any]) -> Callable[..., Any]:
        """Assign the doc string from func to target."""
        target.__doc__ = func.__doc__
        return target

    return decorator


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


class Solr:
    """Class that interacts with the apache solr server."""

    def __init__(self) -> None:
        self._solr_server = f'{cfg.get("solr.host")}:{cfg.get("solr.port")}'
        self._solr_cores = cfg.get("solr.core"), "latest"

    def get_solr_url(self, version: bool = False) -> str:
        """Get the url of the solr right solr core.

        Parameters
        ----------
        version: bool, default: False
            Use the core for the versioned datasets.
        """

        if version:
            return f"http://{self._solr_server}/solr/{self._solr_cores[0]}"
        return f"http://{self._solr_server}/solr/{self._solr_cores[1]}"

    def _execute_single_future(self, future: Dict[str, str]) -> None:
        """Execute a scheduled future."""
        code = future["future"]
        path = future["file"]
        reindex = path.startswith("future:")
        code_hash = future["future_id"]
        if not code:
            code = json.dumps(
                futures.FutureCodeDB.objects.get(code_hash_id=code_hash).code
            )
        temp_dir = TemporaryDirectory()
        temp_file = os.path.join(temp_dir.name, "exec.out")
        with open(temp_file, "w", encoding="utf-8") as stream:
            try:
                nbclient.execute(
                    nbformat.reads(code, as_version=4),
                    cwd=temp_dir.name,
                    stdout=stream,
                    stderr=stream,
                )
                temp_dir.cleanup()
            except Exception as error:
                logger.error("Execution failed: more information in %s", temp_file)
                raise error
        if not reindex:
            return
        url_nv = f"{self.get_solr_url(version=False)}/update/json?commit=true"
        url_v = f"{self.get_solr_url(version=True)}/update/json?commit=true"
        path_e = path.replace(":", "\\:")
        try:
            for nn, url in enumerate([url_nv, url_v]):
                logger.debug("Deleting %s in %s", path, url)
                request = {"delete": {"query": f"file:{path_e}"}}
                res = requests.post(url, json=request, timeout=3)
                res.raise_for_status()
        except requests.HTTPError:
            raise ValueError(f"Solr request to {url} failed: {res.text}")
        except Exception as error:
            raise ValueError(f"Could not connect to {url}: {error}:")

    def execute_solr_futures(self, futures: Iterable[Dict[str, str]]) -> None:
        """Create datasets that have been registered for future executions.

        This methods takes a strings representing a jupyter notebook and
        executes the code.

        Parameters
        ----------
        future:
            A list holding a dictionary with the information on how this
            future is created (code) and the name of the file path for this
            future dataset in the databrowser.
        """
        if not futures:
            return
        with ThreadPoolExecutor() as pool:
            pydev = os.environ.get("PYDEVD_DISABLE_FILE_VALIDATION")
            log_level = logger.level
            try:
                os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
                logger.setLevel(logging.ERROR)
                with get_spinner("Executing futures", clear=True):
                    list(pool.map(self._execute_single_future, futures))
            finally:
                if pydev:
                    os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = pydev
                logger.setLevel(log_level)
        import time

        time.sleep(1)

    def get_file_attributes(
        self,
        path: str,
        field: str,
        uniq_key: Literal["uri", "file"] = "uri",
        multiversion: bool = False,
    ) -> Union[str, List[str]]:
        """Query the databrowser for a field entry.

        Parameters
        ----------
        path:
            The name of the file/uri value.
        field:
            The name of the field information that should be queried.
        uniq_key:
            Indication whether the path parameter is a file or a uri field.

        Returns
        -------
        Union[str, List[str]]: The associated field.
        """
        params: Dict[str, str] = {
            "q": f'{uniq_key}:"{path}"',
            "rows": "1",
            "fl": field,
            "wt": "json",
        }
        url = f"{self.get_solr_url(multiversion)}/select"
        try:
            res = requests.get(url, params=params, timeout=5)
            res.raise_for_status()
        except (requests.HTTPError, requests.ConnectionError):
            logger.debug("Connection to %s with params %s failed", url, params)
            return ""
        return res.json().get("response", {}).get("docs", [{}])[0].get(field, "")

    def post(self, metadata: List[Dict[str, Union[str, List[str]]]]) -> None:
        """Post user metadata to the solr core.

        Parameters
        ----------
        metadata:
            List of metadata that is posted to the solr server.

        Raises
        ------
        ValueError: If the posting the data failed.
        """

        no_version: List[Dict[str, Union[str, List]]] = []
        versioned: List[Dict[str, Union[str, List]]] = []
        for _data in metadata:
            version = _data.get("version", "")
            if version:
                _data["file_no_version"] = cast(str, _data["file"]).replace(
                    "/%s/" % version, "/"
                )
            else:
                _data["file_no_version"] = _data["file"]
            _data["time"] = get_solr_time_range(cast(str, _data.pop("time", "fx")))
            _data.setdefault("cmor_table", _data.get("time_frequency", "none"))
            _data.setdefault("realm", "user-data")
            _data.setdefault("project", f"user-{getuser()}")
            no_version.append({k: v for k, v in _data.items() if k != "version"})
            versioned.append(_data)
        url_nv = f"{self.get_solr_url(version=False)}/update/json?commit=true"
        url_v = f"{self.get_solr_url(version=True)}/update/json?commit=true"
        batch_data = [no_version, versioned]
        try:
            for nn, url in enumerate([url_nv, url_v]):
                logger.debug("Sending %s to %s", url, batch_data[nn])
                res = requests.post(url, json=batch_data[nn], timeout=3)
                res.raise_for_status()
        except requests.HTTPError:
            raise ValueError(f"Solr request to {url} failed: {res.text}")
        except Exception as error:
            raise ValueError(f"Could not connect to {url}: {error}:")


class PluginStatus:
    """Interact with a plugin application.

    With help of this functionality you can:

        - Check if a plugin is still running.
        - Get all results (data or plot files) of a plugin.
        - Check the configuration of a plugin.
        - Wait until the plugin is finished.

    Parameters
    ----------
    history_id:
        The id of the plugin application history. You can get the id by
        consulting the :py:meth:``freva.history`` search method.

    Example
    -------

    The output of the ``freva.run_plugin`` method is an instance of the
    :py:class:``freva.PluginStatus`` class. That means you can directly use the output of
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
        res = freva.get_plugin_status(hist["id"])
        print(rest.status)
    """

    def __init__(self, history_id: int) -> None:
        self._id: int = history_id

    def __repr__(self) -> str:
        return (
            f"PluginStatus('{self.plugin}', "
            f"config={str(self.configuration)}, status={self.status})"
        )

    @property
    def id(self) -> int:
        """Get the history id of the plugin run."""
        return self._id

    @property
    def _hist(self) -> dict[str, Any]:
        log_level = logger.level
        logger.setLevel(logging.ERROR)
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
        with get_spinner("Wait for plugin to finish") as spinner:
            while self.status in ("running", "scheduled", "unkown"):
                time.sleep(dt)
                n_itt += 1
                if n_itt > max_itt:
                    spinner.update(text=str(spinner.text) + "ouch")
                    raise ValueError("Plugin did not finish")

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
