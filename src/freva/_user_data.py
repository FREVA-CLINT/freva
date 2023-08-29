"""Update user data in the apache solr data search server."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Union, cast

import appdirs
import lazy_import
import nbformat
import nbparameterise as nbp
import yaml

from evaluation_system.misc import logger
from evaluation_system.misc.exceptions import (
    ConfigurationException,
    ValidationError,
)

User = lazy_import.lazy_class("evaluation_system.model.user.User")
config = lazy_import.lazy_module("evaluation_system.misc.config")
SolrCore = lazy_import.lazy_class("evaluation_system.model.solr_core.SolrCore")
DataReader = lazy_import.lazy_class("evaluation_system.api.user_data.DataReader")
get_output_directory = lazy_import.lazy_function(
    "evaluation_system.api.user_data.get_output_directory"
)
from .utils import Solr, handled_exception

__all__ = ["UserData"]


@dataclass
class UserData:
    """Data class that handles user data requests. With help of this class
    users can add their own data to the databrowser, (re)-index data in the
    databrowser, delete data in the databrowser or add datasets to the
    databrowser that doesn't even exist yet but can be created on demand in
    the future (future dataset)."""

    def __post_init__(self):
        self.solr = Solr()

    @classmethod
    def get_futures(cls, full_paths: bool = True) -> List[str]:
        """Get all system wide and user future definitions.

        This method searches all system paths including a custom path that
        can be set via the "FREVA_FUTURE_DIR" variable and gets all available
        files holding the recipes of how to (re)create datasets in the future.

        Parameters
        ----------
        full_paths: bool, default: True
            Return full paths to the datasets, if False then only the names
            of the future definitions are returned.

        Returns
        -------
        list: All future file definitions.
        """
        user_futures = [
            os.path.join(appdirs.user_config_dir("freva"), "futures"),
            os.path.join(cls._get_user_dir(), "futures"),
        ]
        for user_future in user_futures:
            Path(user_future).mkdir(exist_ok=True, parents=True, mode=0o775)
        user_futures.append(os.environ.get("FREVA_FUTURE_DIR", ""))
        _dirs = [
            Path(d).expanduser().absolute()
            for d in (
                os.path.join(sys.prefix, "freva", "futures"),
                *user_futures,
            )
            if d
        ]
        futures = []
        for _dir in _dirs:
            for suffix in (".ipynb", ".cwl"):
                if full_paths:
                    futures += [
                        str(f)
                        for f in _dir.rglob(f"*{suffix}")
                        if "-checkpoint" not in str(f)
                    ]
                else:
                    futures += [
                        f.with_suffix("").name
                        for f in _dir.rglob(f"*{suffix}")
                        if "-checkpoint" not in str(f)
                    ]
        return futures

    @staticmethod
    def _get_user_dir() -> str:
        try:
            return str(get_output_directory() / f"user-{User().getName()}")
        except ConfigurationException:
            config.reloadConfiguration()
            return str(get_output_directory() / f"user-{User().getName()}")

    @property
    def user_dir(self) -> Path:
        """Get the user output directory."""
        return Path(self._get_user_dir())

    def _validate_user_dirs(
        self, *crawl_dirs: os.PathLike, **kwargs: bool
    ) -> tuple[Path, ...]:
        root_path = self.user_dir
        user_paths: tuple[Path, ...] = ()
        _allow_others = kwargs.get("_allow_others", False)
        for crawl_dir in crawl_dirs or (root_path,):
            crawl_dir = Path(crawl_dir or root_path).expanduser().absolute()
            try:
                _ = crawl_dir.relative_to(root_path)
            except ValueError:
                if _allow_others is False:
                    raise ValidationError(
                        f"You are only allowed to crawl data in {root_path}"
                    )
            user_paths += (crawl_dir,)
        return user_paths

    @staticmethod
    def _set_add_method(
        how: str,
    ) -> Callable[[os.PathLike, os.PathLike], None]:
        choices = "copy, link, move, symlink, cp, ln, mv"
        if how in ["copy", "cp"]:
            return shutil.copy
        if how in ["symlink", "ln"]:
            return os.symlink
        if how in ["move", "mv"]:
            return shutil.move
        if how in ["link"]:
            return os.link
        raise ValueError(f"Invalid Method: valid methods are {choices}")

    @handled_exception
    def register_future(
        self,
        future: Union[str, Path],
        variable_file: Union[str, Path, None] = None,
        **facets: Union[str, List[str]],
    ) -> None:
        """Register datasets in the databrowser that can be created on demand.

        The future concept allows users to add datasets to the databrowser
        that can be created on demand in the future. That is rather than
        creating existing datasets once, users can register the creation of
        a dataset that gets created when it is actually analysed. This can
        save significant about of disk space and allows for deeper insights
        on the usefulness of certain datasets.

        The datasets are created based on a recipe. Please consult the
        freva documentation for information on how to created those recipes.

        Parameters
        ----------
        future:
            Name or file path of the future recipe.
        variable_file:
            Json or Yaml file holding additional variables that are not
            databrowser search keys (facets). Databrowser search facets
            are set separately.
        **facets:
            Databrowser search facets. These facets are used to add information
            to the databrowser.
        """
        suffix = Path(variable_file or "").suffix
        if variable_file:
            with open(variable_file) as f_obj:
                if suffix.lower() in (".json"):
                    variables = json.load(f_obj)
                else:
                    variables = yaml.safe_load(f_obj)
        else:
            variables = {}
        futures = {}
        for path in map(Path, self.get_futures()):
            futures[path.with_suffix("").name] = path
        future_name = Path(future).with_suffix("").name
        try:
            future_file = futures[future_name]
        except KeyError:
            valid_futures = ", ".join(futures.keys())
            raise ValueError(f"Future not valid, valid futures are: {valid_futures}")

        logger.debug("Adding future to databrowser")
        self.solr.post(
            [
                self._parametrise_notebook(
                    future_file,
                    {k: v for (k, v) in facets.items() if v},
                    variables,
                )
            ]
        )

    @staticmethod
    def _parametrise_notebook(
        inp_notebook: Path,
        solr_variables: Dict[str, Union[List[str], str]],
        variables: Dict[str, Any],
    ) -> Dict[str, Union[str, List[str]]]:
        """Set all variables in the notebook."""

        notebook = nbformat.reads(inp_notebook.read_text(), as_version=4)

        # Update the solr parameters
        solr_params = nbp.parameter_values(
            nbp.extract_parameters(notebook, tag="solr-parameters"),
            **solr_variables,
        )
        # Update any other variable definition
        other_params = nbp.parameter_values(
            nbp.extract_parameters(notebook, tag="parameters"), **variables
        )

        notebook = json.dumps(
            nbp.replace_definitions(
                nbp.replace_definitions(notebook, solr_params), other_params
            ),
            indent=3,
        )
        facets = {p.name: p.value for p in solr_params}
        solr_variables.update(facets)
        facets = solr_variables
        file_name: List[str] = []
        parts = []
        drs_ = config.get_drs_config()["crawl_my_data"]
        for key in drs_["parts_dir"] + drs_["parts_file_name"]:
            if key not in parts:
                parts.append(key)
        for key in parts:
            value = facets.get(key)
            if isinstance(value, list):
                value_s = "".join([v[0].upper() + v[1:].lower() for v in value])
            elif value:
                value_s = str(value)
            else:
                continue
            file_name.append(value_s)
        facets["future"] = notebook
        facets["dataset"] = "future"
        facets["file"] = facets["uri"] = f"future://{'_'.join(file_name)}"
        logger.debug(
            "Prametrizing notebook with: %s and file name %s",
            facets,
            facets["file"],
        )
        return facets

    @handled_exception
    def add(
        self,
        product: str,
        *paths: os.PathLike,
        how: str = "copy",
        override: bool = False,
        **defaults: str,
    ) -> None:
        """Add custom user files to the databrowser.

        To be able to add data to the databrowser the file names must
        follow a strict standard and the files must reside in a
        specific location. This ``add`` method takes care about the correct
        file naming and location. No pre requirements other than the file has
        to be a valid ``netCDF`` or ``grib`` file are assumed. In other words
        this method places the user data with the correct naming structure to
        the correct location.

        Parameters
        ----------
        product: str
            Product search key the newly added data can be found.
        *paths: os.PathLike
            Filename(s) or Directories that are going to be added to the
            databrowser. The files will be added into the central user
            directory and named according the CMOR standard. This ensures
            that the data can be added into the databrowser.
            **Note:** Once the data has been added into the databrowser it can
            be found via the ``user-<username>`` project.
        how: str, default: copy
            Method of how the data is added into the central freva user directory.
            Default is copy, which means your data files will be replicated.
            To avoid a this redundancy you can set the ``how`` keyword to
            ``symlink`` for symbolic links or ``link`` for creating hard links
            to create symbolic links or ``move`` to move the data into the central
            user directory entirely.
        override: bool, default: False
            Replace existing files in the user data structre
        experiment: str, default: None
            By default the method tries to deduce the *experiment* information from
            the metadata. To overwrite this information the *experiment* keyword
            should be set.
        institute: str, default: None
            By default the method tries to deduce the *institute* information from
            the metadata. To overwrite this information the *institute* keyword
            should be set.
        model: str, default: None
            By default the method tries to deduce the *model* information from
            the metadata. To overwrite this information the *model* keyword
            should be set.
        variable: str, default: None
            By default the method tries to deduce the *variable* information from
            the metadata. To overwrite this information the *variable* keyword
            should be set.
        time_frequency: str, default: None
            By default the method tries to deduce the *time_frequency* information
            from the metadata. To overwrite this information the *time_frequency*
            keyword should be set.
        ensemble: str, default: None
            By default the method tries to deduce the *ensemble* information from
            the metadata. To overwrite this information the *ensemble* keyword
            should be set.

        Raises
        ------
        ValueError: If metadata is insufficient, or product key is empty


        Example
        -------

        Suppose you've gotten data from somewhere and want to add this data into the
        databrowser to make it accessible to others. In this specific
        example we assume that you have stored your `original` data in the
        ``/tmp/my_awesome_data`` folder.
        E.g ``/tmp/my_awesome_data/outfile_0.nc...tmp/my_awesome_data/outfile_9.nc``
        The routine will try to gather all necessary metadata from the files. You'll
        have to provide additional metadata if mandatory keywords are missing.
        To make the routine work you'll have to provide the ``institute``, ``model``
        and ``experiment`` keywords:

        .. execute_code::

            from freva import UserData, databrowser
            user_data = UserData()
            # You can also provide wild cards to search for data
            user_data.add("eur-11b", "/tmp/my_awesome_data/outfile_?.nc",
                              institute="clex", model="UM-RA2T",
                              experiment="Bias-correct")
            # Check the databrowser if the data has been added
            for file in databrowser(experiment="bias*"):
                print(file)

        By default the data is copied. By using the ``how`` keyword you can
        also link or move the data.
        """
        crawl_dirs: list[Path] = []
        facets = (
            "experiment",
            "institute",
            "model",
            "variable",
            "time_frequency",
            "ensemble",
        )
        _project = defaults.pop("_project", None)
        search_keys = {k: defaults[k] for k in facets if defaults.get(k)}
        search_keys["product"] = product
        search_keys["project"] = _project or f"user-{User().getName()}"
        search_keys["realm"] = "user_data"
        search_keys.setdefault("ensemble", "r0i0p0")
        for path in paths:
            p_path = Path(path).expanduser().absolute()
            u_reader = DataReader(p_path, **search_keys)
            for file in u_reader:
                new_file = u_reader.file_name_from_metdata(file, override=override)
                new_file.parent.mkdir(exist_ok=True, parents=True, mode=0o2775)
                if new_file.exists() and override:
                    new_file.unlink()
                self._set_add_method(how)(file, new_file)
                if new_file.parent not in crawl_dirs:
                    crawl_dirs.append(new_file.parent)
        if not crawl_dirs:
            warnings.warn("No files found", category=UserWarning)
            return
        self.index(*crawl_dirs, _allow_others=_project is not None)

    @handled_exception
    def delete(self, *paths: os.PathLike, delete_from_fs: bool = False) -> None:
        """Delete data from the databrowser.

        The methods deletes user data from the databrowser.

        Parameters
        ----------

        *paths: os.PathLike
            Filename(s) or Directories that are going to be from  the
            databrowser.
        delete_from_fs: bool, default : False
            Do not only delete the files from the databrowser but also from their
            central location where they have been added to.

        Raises
        ------
        ValidationError:
            If crawl_dirs do not belong to current user.

        Example
        -------

        Any data in the central user directory that belongs to the user can
        be deleted from the databrowser and also from the central data location:

        .. execute_code::

            from freva import UserData
            user_data = UserData()
            user_data.delete(user_data.user_dir)

        """
        solr_core = SolrCore(core="files")
        for path in paths:
            for file in DataReader(Path(path).expanduser().absolute()):
                self._validate_user_dirs(file)
                solr_core.delete_entries(str(file))
                if delete_from_fs:
                    file.unlink()

    @handled_exception
    def index(
        self,
        *crawl_dirs: os.PathLike,
        dtype: str = "fs",
        continue_on_errors: bool = False,
        **kwargs: bool,
    ) -> None:
        """Index and add user output data to the databrowser.

        This method can be used to update the databrowser for existing user data

        Parameters
        ----------
        crawl_dirs:
            The data path(s) that needs to be crawled.
        dtype:
            The data type, currently only files on the file system are supported.
        continue_on_errors:
            Continue indexing on error.

        Raises
        ------
        ValidationError:
            If crawl_dirs do not belong to current user.

        Example
        -------

        If data has been removed from the databrowser it can be re added using
        the ``index`` method:

        .. execute_code::

            from freva import UserData
            user_data = UserData()
            user_data.index()

        """
        if dtype not in ("fs",):
            raise NotImplementedError("Only data on POSIX file system is supported")
        log_level = logger.level
        try:
            logger.setLevel(logging.ERROR)
            print("Status: crawling ...", end="", flush=True)
            solr_core = SolrCore(core="latest")
            for crawl_dir in self._validate_user_dirs(*crawl_dirs, **kwargs):
                data_reader = DataReader(crawl_dir)
                solr_core.load_fs(
                    crawl_dir,
                    chunk_size=1000,
                    abort_on_errors=not continue_on_errors,
                    drs_type=data_reader.drs_specification,
                )
            print("ok", flush=True)
        finally:
            logger.setLevel(log_level)
