"""Module that handles so called future dataset.

Future dataset are dataset that do not exist yet but the system has a
knowledge of how to create them when they are needed hence the term `future`.

Future dataset need to be `registered`. Registering means a recipe of how to
create the dataset as well as the metadata (search facets) are added to the
databrowser. If the databrowser encounters a future it can then be executed
and the dataset is created.

The dataset is also saved to a database to keep track of all registered
futures. This way the future datasets can be crawled and added to a solr.
"""
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union, cast

import appdirs
import lazy_import
import nbclient
import nbformat
import nbparameterise as nbp
import yaml

from evaluation_system.misc import logger
from evaluation_system.model import futures

from ._user_data import UserData
from .utils import PluginStatus, Solr, copy_doc_from, handled_exception

cfg = lazy_import.lazy_module("evaluation_system.misc.config")
freva_history = lazy_import.lazy_module("evaluation_system.model.history.models")
get_solr_time_range = lazy_import.lazy_callable(
    "evaluation_system.misc.utils.get_solr_time_range"
)
pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
parameters = lazy_import.lazy_module("evaluation_system.api.parameters")
DataReader = lazy_import.lazy_class("evaluation_system.api.user_data.DataReader")


class Futures:
    """Class that adds future datasets to the database."""

    def __init__(
        self,
        code: str,
        file_name: str,
        history_id: int = -1,
        register: bool = False,
    ) -> None:
        self.notebook = nbformat.reads(code, as_version=4)
        self.file_name = file_name
        self.history_id = history_id
        self._user_data = UserData("futures")
        if register:
            self._add_future_to_db()

    def add_data(
        self,
        project: str,
        product: str,
        *paths: os.PathLike,
        history_id: Optional[int] = None,
        **solr_parameters: str,
    ) -> None:
        """Add future files to the databrowser.

        To be able to add data to the databrowser the file names must
        follow a strict standard and the files must reside in a
        specific location. This ``add`` method takes care about the correct
        file naming and location. No pre requirements other than the file has
        to be a valid ``netCDF`` or ``grib`` file are assumed. In other words
        this method places the user data with the correct naming structure to
        the correct location.

        Parameters
        ----------
        project:
            The <project> databrowser search facet.
        product:
            The <product> databrowser search facet.
        *paths: os.PathLike
            Filename(s) or Directories that are going to be added to the
            databrowser. The files will be added into the central user
            directory and named according the CMOR standard. This ensures
            that the data can be added into the databrowser.
            **Note:** Once the data has been added into the databrowser it can
            be found via the ``user-<username>`` project.
        history_id:
            If the current files were (re)created by a freva plugin give the
            history_id to delete the history entries from the database.
        **solr_parameters:
            Solr parameters that should not or can't be retrieved from the
            data files.

        Raises
        ------
        ValueError: If metadata is insufficient, or product key is empty
        """
        solr_parameters["_project"] = project
        solr_parameters["future_id"] = self.hash
        new_files = self._user_data.add(product, *paths, how="move", **solr_parameters)
        files_db = self.files_db
        files_db.file_names = new_files
        files_db.save()
        if history_id:
            try:
                hist_obj = freva_history.History.objects.get(id=history_id)
                hist_obj.delete()
            except freva_history.History.DoesNotExist:
                pass

    @staticmethod
    def _notebook_to_hash(
        notebook: nbformat.notebooknode.NotebookNode, comment: str = "#"
    ) -> str:
        """Get only the code cells of the notebook."""
        pure_code = ""
        sha256_hash = hashlib.sha256()
        for cell in notebook.cells:
            if cell.cell_type == "code" and cell.source.strip():
                no_comment_code = "\n".join(
                    [
                        line.strip()
                        for line in cell.source.splitlines()
                        if not line.strip().startswith("#")
                        and not line.startswith("future_id")
                        and line.strip()
                    ]
                )
                no_inline_comments_code = re.sub(
                    r"{}.*$".format(comment),
                    "",
                    no_comment_code,
                    flags=re.MULTILINE,
                )
                pure_code += no_inline_comments_code + "\n"
        sha256_hash.update("".join(sorted(pure_code)).encode("utf-8"))
        return sha256_hash.hexdigest()

    @cached_property
    def hash(self) -> str:
        """Calculate the sha256 hash sum of the code."""
        return self._notebook_to_hash(self.notebook)

    @property
    def code_db(self) -> futures.FutureCodeDB:
        """Get an instance of the code database table."""
        try:
            return futures.FutureCodeDB.objects.get(code_hash_id=self.hash)
        except futures.FutureCodeDB.DoesNotExist:
            return futures.FutureCodeDB(
                code_hash=self.files_db,
                history_id=self.history_id,
                code=self.notebook,
                file_name=self.file_name,
            )

    @property
    def files_db(self) -> futures.FutureFilesDB:
        """Get in instance of the files database table."""
        try:
            return futures.FutureFilesDB.objects.get(code_hash=self.hash)
        except futures.FutureFilesDB.DoesNotExist:
            return futures.FutureFilesDB(
                code_hash=self.hash,
                file_names=[self.file_name],
            )

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
            os.path.join(UserData.get_user_dir(), "futures"),
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

    @classmethod
    @handled_exception
    def from_existing_code_hash(
        cls, code_hash: Optional[str] = None, history_id: Optional[int] = None
    ) -> "Futures":
        """Create an instance of the class from a already registered future.

        This method creates an instance of the futures class from an already
        existing entry in the futures database. This can be useful to alter
        existing entries.


        Parameters
        ----------
        code_hash:
            The hash value of the code that is in the database. The code
            hashes are the main id's to identify the entries in the futures
            database tables. If None given (default) the code will try to
            search for a given history id
        history_id:
            The freva plugin history id the future belongs to. If the future
            was registered by a freva plugin history you can create an instance
            of the futures class by giving this history id.

        Raises
        ------
            ValueError: If no entries in the database table were found.

        Example
        -------

        .. code:: python

            import freva
            history_id = freva.history(plugin="ClimdexCalc", limit=1)[0]["id"]
            future = freva.from_existing_code_hash(history_id=history_id)

        """
        try:
            if code_hash:
                entry = futures.FutureCodeDB.objects.get(code_hash_id=code_hash)
            elif history_id:
                entry = futures.FutureCodeDB.objects.get(history_id=history_id)
            else:
                raise ValueError("Code hash or history id must be valid.")
        except futures.FutureCodeDB.DoesNotExist:
            raise ValueError("Could not find any entries.")
        return cls(
            json.dumps(entry.code),
            entry.file_name,
            register=False,
            history_id=entry.history_id,
        )

    @classmethod
    @handled_exception
    def register_future_from_history_id(
        cls,
        history_id: int,
    ) -> "Futures":
        """Register dataset in the databrowser that can be created on demand.

        The future concept allows users to add datasets to the databrowser
        that can be created on demand in the future. That is rather than
        creating existing datasets once, users can register the creation of
        a dataset that gets created when it is actually analysed. This can
        save significant about of disk space and allows for deeper insights
        on the usefulness of certain datasets.

        The datasets are created based on the application of a already
        applied freva plugin that produced dataset(s).

        Parameters
        ----------
        hisotry_id:
            The history id of the plugin that has been applied. To find
            out the history id you can consut the :py:func:``freva.history``
            method.

        Example
        -------
        Let's assume we have a plugin called ClimdexCalc that calculates
        indices of extreme weahter conditions. The plugin has been applied
        and it's ouput data is can be presnt or already be removed from the
        storage system. We want to turn this specific plugin appliction
        into a future dataset that can be created on demand. To do so we
        get the history id of the freva plugin appliction and call the
        py:meth:``freva.register_future_from_history_id`` id. We first get the
        history id of the plugin run (say the last plugin that we have applied
        with the name 'ClimdexCalc').

        .. code:: python

            import freva
            history_id = freva.history(plugin="ClimdexCalc", limit=1)[0]["id"]
            future = freva.register_future_from_history_id(history_id)
        """
        plugin_run = PluginStatus(history_id)
        plugin_cls = pm.get_plugin_instance(plugin_run.plugin.lower())
        complete_conf = plugin_cls.setup_configuration(
            plugin_run.configuration, recursion=True
        )
        params = plugin_cls.__parameters__
        user_facets = cls.get_future_data_facets()
        solr_parameters, all_parameters = {}, {}
        for key, value in complete_conf.items():
            parameter_cls = params.get_parameter(key)
            if key in user_facets:
                solr_parameters[key] = value
            elif isinstance(parameter_cls, parameters.SolrField):
                solr_parameters[parameter_cls.facet] = value
            if "".join(key.split("_")) in (
                "outdir",
                "outputdir",
                "outputdirectory",
                "output",
            ):
                all_parameters[key] = "outdir"
            elif "".join(key.split("_")) in (
                "cachedir",
                "cachedir",
                "cachedirectory",
                "cache",
            ):
                all_parameters[key] = "cachedir"
            else:
                all_parameters[key] = value

        reader = DataReader(
            plugin_run.get_result_paths(),
            drs_specification="futures",
            **solr_parameters,
        )
        metadata: Dict[str, list[str]] = defaultdict(list)
        for file_path in reader:
            for key, value in reader.get_metadata(file_path).items():
                if value:
                    metadata[key].append(value)
        solr_variables: Dict[str, Union[str, List[str]]] = {}
        for key in metadata:
            values = list(set(metadata[key]))
            if len(values) == 1:
                solr_variables[key] = values[0]
            else:
                solr_variables[key] = values
        solr_variables.setdefault("realm", "atmos")
        code_cell = (
            f'res = freva.run_plugin("{plugin_run.plugin}",\n   batchmode=False,'
            "\n   " + "   ".join([f"{k}={k}, \n" for k in all_parameters]) + ")"
        )
        solr_facets = cls.parameterise_notebook(
            (Path(__file__).parent / "future_template.json").read_text(),
            solr_variables=solr_variables,
            variables=all_parameters,
            replace_by_tag={"code": code_cell},
            new_variables="add",
        )
        Solr().post([solr_facets])
        return cls(
            cast(str, solr_facets["future"]),
            cast(str, solr_facets["file"]),
            history_id=history_id,
            register=True,
        )

    @classmethod
    @handled_exception
    def register_future_from_template(
        cls,
        future: Union[str, Path],
        variable_file: Union[str, Path, None] = None,
        **facets: Union[str, List[str]],
    ) -> "Futures":
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
                if suffix.lower() == ".json":
                    variables = json.load(f_obj)
                else:
                    variables = yaml.safe_load(f_obj)
        else:
            variables = {}
        futures_dict = {}
        for path in map(Path, cls.get_futures()):
            futures_dict[path.with_suffix("").name] = path
        future_name = Path(future).with_suffix("").name
        try:
            future_file = futures_dict[future_name]
        except KeyError:
            valid_futures = ", ".join(futures_dict.keys())
            raise ValueError(f"Future not valid, valid futures are: {valid_futures}")

        logger.debug("Adding future to databrowser")
        code = future_file.read_text()
        solr_facets = cls.parameterise_notebook(
            code,
            {k: v for (k, v) in facets.items() if v},
            variables,
        )
        Solr().post([solr_facets])
        return cls(
            cast(str, solr_facets["future"]),
            cast(str, solr_facets["file"]),
            history_id=-1,
            register=True,
        )

    def _add_future_to_db(self) -> None:
        """Add a future to the database."""
        kwargs: Dict[str, Union[str, int]] = {}
        if self.history_id > 0:
            kwargs = {"history_id__icontains": self.history_id}
        else:
            kwargs = {"code_hash__icontains": self.hash}
        result = futures.FutureCodeDB.objects.filter(**kwargs).first()
        if not result:
            self.files_db.save()
            self.code_db.save()

    @classmethod
    def create_future_file_name(
        cls, solr_parameters: Dict[str, Union[str, List[str]]]
    ) -> Path:
        """Create the filename of a future dataset."""
        drs = cfg.get_drs_config()["futures"]
        parts: Dict[str, List[str]] = {"parts_dir": [], "parts_file_name": []}
        for key in parts:
            for facet in drs[key]:
                value = solr_parameters.get(facet)
                if isinstance(value, list):
                    value_s = "".join(
                        [v[0].upper() + v[1:].lower() for v in sorted(value)]
                    )
                elif value:
                    value_s = str(value)
                else:
                    continue
                parts[key].append(value_s)
        return Path(drs["root_dir"]).joinpath(*parts["parts_dir"]) / "_".join(
            parts["parts_file_name"]
        )

    @staticmethod
    def get_future_data_facets(
        drs: Optional[Dict[str, Union[str, List[str]]]] = None
    ) -> List[str]:
        """Get the solr search facets that are defined by the future drs.

        This methods gets the minimum amount of solr search facets that
        define a complete solr dataset.

        Parameters
        ----------
        drs:
            The predefined directory reference syntax specifications,
            if None are given (default) the specifications are loaded from
            the specifications file (drs_config.toml).

        Returns
        -------
        List[str]:
            List of facet names that define a solr dataset.

        """
        parts = []
        drs_ = cast(
            Dict[str, Union[str, List[str]]],
            drs or cfg.get_drs_config()["futures"],
        )
        for key in cast(List[str], drs_["parts_dir"]) + cast(
            List[str], drs_["parts_file_name"]
        ):
            if key not in parts:
                parts.append(cast(str, key))
        return parts

    @classmethod
    def parameterise_notebook(
        cls,
        code: str,
        solr_variables: Dict[str, Union[List[str], str]],
        variables: Dict[str, Any],
        replace_by_tag: Optional[Dict[str, str]] = None,
        new_variables: Literal["add", "ignore", "error"] = "ignore",
        uri: bool = True,
    ) -> Dict[str, Union[str, List[str]]]:
        """Parameterise a jupyter notebook according according.

        The method parameterises a jupyter notebook according to given input
        variables and solr search facets that have to be set in the notebook.

        Parameters
        ----------
        code:
            String representation of the jupyter notebook that is executed
            to create the dataset.
        solr_variables:
            The output solr variables that the code the jupyter notebooks
            executes will create. *Note:* The solr_variables have to be
            defined in a cell that is tagged with the name ``solr-parameters``
            in the notebook.
        variables:
            Additional variables that are needed to run the code.
            *Note:* The variables have to bee define in a cell that is tagged
            with the name ``parameters`` in the notebook.
        replace_by_tag:
            Replace all cells that are tagged with keys in this dictionary
            by this values, if None (default) no replacement will be performed.
        new_variables:
            How to treat parameters that are not define in the notebook.
        uri:
            Create an uri starting with future://.

        Returns
        -------
        Dict:
            A dictionary with all necessary information to add this future to
            the databrowser.
        """
        notebook = nbformat.reads(code, as_version=4)

        # Update the solr parameters
        solr_params = nbp.parameter_values(
            nbp.extract_parameters(notebook, tag="solr-parameters"),
            new=new_variables,
            **solr_variables,
        )
        # Update any other variable definition
        other_params = nbp.parameter_values(
            nbp.extract_parameters(notebook, tag="parameters"),
            new=new_variables,
            **variables,
        )
        replace_by_tag = replace_by_tag or {}
        if replace_by_tag:
            for nn, cell in enumerate(notebook.cells):
                tags = [
                    t
                    for t in cell.get("metadata", {}).get("tags", [])
                    if t in replace_by_tag
                ]
                if cell["cell_type"] == "code" and tags:
                    notebook["cells"][nn]["source"] = cell.source.replace(
                        cell.source, replace_by_tag[tags[0]]
                    )

        notebook = nbp.replace_definitions(
            nbp.replace_definitions(notebook, solr_params, tag="solr-parameters"),
            other_params,
            tag="parameters",
        )
        facets = {p.name: p.value for p in solr_params}
        solr_variables.update(facets)
        facets = solr_variables
        # TODO: This is very awkward, we have to add the hash of the notebook
        # to the notebook, but doing so would result in a different notebook
        # hash. The closure of the problem is to instruct the hash generator
        # to ignore code that defines the hash (future_id = ... ). But even then
        # we have to generate the notebook twice. First get the notebook with
        # all its parameters and generate the hash. Then re-add the hash
        # to the notebook.
        facets["future_id"] = cls._notebook_to_hash(notebook)
        other_params.append(nbp.Parameter("future_id", str, value=facets["future_id"]))
        notebook = nbp.replace_definitions(notebook, other_params, tag="parameters")
        # The hash values from before adding the hash and after adding the
        # hash have to be the same, lets perform a smoke test:
        if facets["future_id"] != cls._notebook_to_hash(notebook):
            raise ValueError(
                (
                    "Could not get closure while adding hash value:"
                    " hash values differ."
                )
            )
        facets["future"] = json.dumps(notebook, indent=3)
        facets["dataset"] = "future"
        file_name = cls.create_future_file_name(facets)
        if uri:
            facets["file"] = facets["uri"] = f"future://{file_name}"
        else:
            facets["file"] = facets["uri"] = str(file_name)
        logger.debug(
            "Parametrising notebook with: %s and file name %s",
            facets,
            facets["file"],
        )
        return facets
