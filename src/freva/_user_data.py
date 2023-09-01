"""Update user data in the apache solr data search server."""

from __future__ import annotations

from importlib import import_module
import logging
import os
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Union, cast

import lazy_import

from evaluation_system.misc import logger
from evaluation_system.misc.exceptions import (
    ConfigurationException,
    ValidationError,
)

User = lazy_import.lazy_class("evaluation_system.model.user.User")
config = lazy_import.lazy_module("evaluation_system.misc.config")
SolrCore = lazy_import.lazy_class("evaluation_system.model.solr_core.SolrCore")
DataReader = lazy_import.lazy_class(
    "evaluation_system.api.user_data.DataReader"
)
get_output_directory = lazy_import.lazy_function(
    "evaluation_system.api.user_data.get_output_directory"
)
from .utils import Solr, handled_exception, get_spinner

__all__ = ["UserData"]


@dataclass
class UserData:
    """Data class that handles user data requests. With help of this class
    users can add their own data to the databrowser, (re)-index data in the
    databrowser, delete data in the databrowser or add datasets to the
    databrowser that doesn't even exist yet but can be created on demand in
    the future (future dataset)."""

    drs_spec: str = "crawl_my_data"

    def __post_init__(self):
        self.solr = Solr()

    @staticmethod
    def get_user_dir(drs_spec: Optional[str] = None) -> str:
        """Get the freva user output directory name."""
        try:
            return str(
                get_output_directory(drs_spec) / f"user-{User().getName()}"
            )
        except ConfigurationException:
            config.reloadConfiguration()
            return str(
                get_output_directory(drs_spec) / f"user-{User().getName()}"
            )

    @property
    def user_dir(self) -> Path:
        """Get the user output directory."""
        return Path(self.get_user_dir(self.drs_spec))

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
        time_aggregation: str, default: mean
            Set the time_aggregation level, that is how the data was aggregated
            along the itme axis, mean, sum, instant values etc.
        cmor_table: str, default: None
            You can override the cmor_table variable, by default the cmor_table
            is set to ``time_frequency``

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

            import freva
            # You can also provide wild cards to search for data
            freva.add_user_data("eur-11b", "/tmp/my_awesome_data/outfile_?.nc",
                                institute="clex", model="UM-RA2T",
                                experiment="Bias-correct")
            # Check the databrowser if the data has been added
            for file in freva.databrowser(experiment="bias*"):
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
        search_keys.setdefault("realm", "user_data")
        search_keys.setdefault("ensemble", "r0i0p0")
        for path in paths:
            p_path = Path(path).expanduser().absolute()
            u_reader = DataReader(p_path, **search_keys)
            for file in u_reader:
                new_file = u_reader.file_name_from_metdata(
                    file, override=override
                )
                new_file.parent.mkdir(exist_ok=True, parents=True, mode=0o2775)
                if new_file.exists() and override:
                    new_file.unlink()
                self._set_add_method(how)(file, new_file)
                if new_file.parent not in crawl_dirs:
                    crawl_dirs.append(new_file.parent)
        if not crawl_dirs:
            warnings.warn("No files found", category=UserWarning)
            return
        self.index(
            *crawl_dirs,
            _allow_others=_project is not None,
            defaults=search_keys,
        )

    @handled_exception
    def delete(
        self, *paths: os.PathLike, delete_from_fs: bool = False
    ) -> None:
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

            import freva
            freva.delete_user_data()

        """
        solr_core = SolrCore(core="files")
        for path in paths or (self.user_dir,):
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
        defaults: Optional[Dict[str, Union[str, List[str]]]] = None,
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
        defautls:
            Set additional information that can be added to the Solr server, be
            careful as there is only a certain set of variables you can set.
            Please refer the databrowser documentation on more information.

        Raises
        ------
        ValidationError:
            If crawl_dirs do not belong to current user.

        Example
        -------

        If data has been removed from the databrowser it can be re added using
        the ``index`` method:

        .. execute_code::

            import freva
            freva.index_user_data()

        """
        if dtype not in ("fs",):
            raise NotImplementedError(
                "Only data on POSIX file system is supported"
            )
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
