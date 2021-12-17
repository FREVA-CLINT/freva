"""
.. moduleauthor:: christopher kadow / Sebastian Illing
.. first version written by estanislao gonzalez

The module encapsulates all methods for accessing files on the system.
These are mainly model and observational and reanalysis data.
"""
from __future__ import annotations
from typing import (
    Optional,
    Generator,
    TypedDict,
    Union,
    Any,
    ClassVar,
    Literal,
    overload,
)
from dataclasses import dataclass, field

import json
from pathlib import Path
import os
import logging
from evaluation_system.misc import config

log = logging.getLogger(__name__)

Activity = str
"""Represents a type of data collection activity for DRS (see Activity from the DRS spec).

    This doesn't prevent typing issues beyond what you'd get with `str` but  I think
    it makes the functions that deal with Activities more clear than simply using `str`
"""

ACTIVITY_BASELINE0: Activity = "baseline0"


@dataclass
class DRSStructure:
    root_dir: str
    """Directory from where this files are to be found. Put through `expanduser` to
        expand `~` then `absolute`.
    """
    parts_dir: list[str]
    """List of subdirectory category names the values they refer to
        (e.g. ['model', 'experiment']).
    """
    parts_dataset: list[str]
    """The components of a dataset name (this data should also be found in parts_dir)."""
    parts_file_name: list[str]
    """Elements composing the file name (no ".nc" though)."""
    parts_time: str
    """Describes how the time part of the filename is formed."""
    data_type: Activity
    """same value as this key structure (for reverse traverse)"""
    defaults: dict[str, str] = field(default_factory=dict)
    """list with values that "shouldn't" be required to be changed (e.g. for
        observations, project=obs4MIPS)
    """
    parts_versioned_dataset: Optional[list[str]] = None
    """If this datasets are versioned then define the version structure of them
        (i.e. include the version number in the dataset name).
    """

    def __post_init__(self) -> None:
        self.root_dir = str(Path(self.root_dir).expanduser().absolute())

    @classmethod
    def from_dict(cls, drs_dict: dict[str, Any]) -> DRSStructure:
        """Creates a DRSStructure from the given dict

        Parameters
        ----------
        drs_dict
            Dictionary containing all DRSStructure fields

        Returns
        -------
        DRSStructure
            DRSStructure created from dict
        """
        d = cls(
            root_dir=drs_dict["root_dir"],
            parts_dir=drs_dict["parts_dir"],
            parts_dataset=drs_dict["parts_dataset"],
            parts_file_name=drs_dict["parts_file_name"],
            parts_time=drs_dict["parts_time"],
            data_type=drs_dict["data_type"],
        )
        if "parts_versioned_dataset" in drs_dict:
            d.parts_versioned_dataset = drs_dict["parts_versioned_dataset"]
        if "defaults" in drs_dict:
            d.defaults = drs_dict["defaults"]

        return d


class FileComponents(TypedDict, total=False):
    root_dir: str
    parts: dict[str, str]


class DRSFile:
    """Represents a file that follows the
    `DRS standard <https://pcmdi.llnl.gov/mips/cmip5/docs/cmip5_data_reference_syntax.pdf>`_.
    """

    # Lazy initialized in find_structure_from_path
    DRS_STRUCTURE_PATH_TYPE: ClassVar[Optional[dict[str, Activity]]] = None
    DRS_STRUCTURE: ClassVar[Optional[dict[Activity, DRSStructure]]] = None

    def __init__(
        self,
        file_dict: Optional[FileComponents] = None,
        drs_structure: Activity = ACTIVITY_BASELINE0,
    ):
        """Creates a DRSfile out of the dictionary containing information
            about the file or from scratch.

        Parameters
        ----------
        file_dict
            dictionary with the DRS component values and keys from which
            this file will be initialized.
        drs_structure
            Which structure is going to be used with this file. Expected
            to be a key value from `DRSFile.DRS_STRUCTURE`
        """
        self.drs_structure = drs_structure
        if not file_dict:
            file_dict = {}
        self.dict = file_dict
        # trim the last slash if present in root_dir
        if "root_dir" in self.dict and self.dict["root_dir"][-1] == "/":
            self.dict["root_dir"] = self.dict["root_dir"][:-1]

    def __repr__(self) -> str:  # pragma: no cover
        """Get the JSON representation.

        This can be used for creating a copy via `from_json`.

        Returns
        -------
        str
            json representation of this object
        """
        return self.to_json()

    def __str__(self) -> str:  # pragma: no cover
        """Return the path of the file.

        See `to_path` for more info.

        Returns
        -------
        str
            path of the file
        """
        return self.to_path()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, DRSFile):
            return NotImplemented
        return self.to_path() < other.to_path()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DRSFile):
            return False
        return self.to_path() == other.to_path()

    def to_json(self) -> str:
        """:returns: (str) the json representation of the dictionary encapsulating the DRS components of this file."""
        return json.dumps(self.dict)

    def to_path(self) -> str:
        """Return the path of the file.

        This returns the full path to the file as described by the DRS
        components. The file is not required to exist.

        Returns
        -------
        str
            The path to the file

        Raises
        ------
        KeyError
            If it can't construct the path because information is missing
            in the DRS components.
        """
        # TODO: check if construction is complete and therefore can succeed
        result = self.dict["root_dir"]
        for key in self.get_drs_structure().parts_dir:
            if key not in self.dict["parts"]:
                raise KeyError("Can't construct path as key %s is missing." % key)
            result = os.path.join(result, self.dict["parts"][key])
        return result

    def to_dataset(self, versioned: bool = False, to_path: bool = False) -> str:
        """Returns dataset information.

        This will return either the dataset's identifier or the path to
        the dataset depending on the value of `to_path`.

        Parameters
        ----------
        versioned
            If the dataset should contain information about the version.
            Note that not all DRS structures are versioned, so in those
            cases where there is just no version information this makes
            no difference.
        to_path
            If true return the path to the dataset, otherwise returns the
            dataset identifier.

        Returns
        -------
        str
            Either the path to the dataset or the dataset identifier

        Raises
        ------
        ValueError
            If `versioned` is True but the structure is not versioned.
        """
        result = []
        structure = self.get_drs_structure()
        if versioned:
            iter_parts = structure.parts_versioned_dataset
            # checking this way as opposed to `if self.is_versioned()` appeases
            # mypy's null check
            if iter_parts is None:
                raise ValueError(f"{self.drs_structure} is not versioned!")
        else:
            iter_parts = structure.parts_dataset

        for key in iter_parts:
            if key in self.dict["parts"]:
                result.append(self.dict["parts"][key])
            elif key in structure.defaults:
                result.append(structure.defaults[key])
        if to_path:
            return os.path.join(structure.root_dir, os.sep.join(result))
        else:
            return ".".join(result)

    def to_dataset_path(self, versioned: bool = False) -> str:
        """Returns the path to the current dataset.

        We are assuming the dataset is a sub-path of all files in it.

        See `to_dataset` for more information.

        Parameters
        ----------
        versioned
            If the dataset should contain information about the version.

        Returns
        -------
        str
            The path to the dataset
        """
        return self.to_dataset(versioned=versioned, to_path=True)

    @property
    def versioned(self) -> bool:
        """If this file is from a DRS structure that is versioned.

        Returns
        -------
        bool
            True is the dataset is versioned, False otherwise
        """
        return self.get_drs_structure().parts_versioned_dataset is not None

    @property
    def version(self) -> Optional[str]:
        """Returns the dataset version of this file

        This returns the version which this file is a part of or None if
        the dataset is not versioned. Note that this is the version of the
        dataset and not of the file since the DRS does not have file
        versions.

        Returns
        -------
        Optional[str]
            The version of the dataset or None if not versioned
        """
        if "version" in self.dict["parts"]:
            return self.dict["parts"]["version"]
        else:
            return None

    @staticmethod
    def _get_structure_prefix_map() -> dict[str, Activity]:
        """Returns reversed map of root_dir to Activity name.

        This will lazily initialize the map if it doesn't already exist.

        Returns
        -------
        dict[str, Activity]
            Map of root_dir to Activity name
        """

        if DRSFile.DRS_STRUCTURE_PATH_TYPE is None:
            DRSFile._load_structure_definitions()
        # ignored due to lazy initialization issue
        return DRSFile.DRS_STRUCTURE_PATH_TYPE  # type: ignore [return-value]

    @overload
    @staticmethod
    def find_structure_from_path(
        file_path: str, allow_multiples: Literal[True]
    ) -> list[Activity]:
        ...

    @overload
    @staticmethod
    def find_structure_from_path(
        file_path: str, allow_multiples: Literal[False]
    ) -> list[Activity]:
        ...

    @overload
    @staticmethod
    def find_structure_from_path(file_path: str) -> Activity:
        ...

    @staticmethod
    def find_structure_from_path(
        file_path: str, allow_multiples: bool = False
    ) -> Union[Activity, list[Activity]]:
        """Return all DRS structures that might be applicable.

        This is resolved by checking if the prefix of any structure paths
        matches that of the given file path. Parsing is not done, so it
        might still fail. This just guarantees that only the structures
        returned here *might* work.

        Parameters
        ----------
        file_path
            Full path to a file, whose drs structure is being searched for.
        allow_multiples
            If true returns a list with all possible structures, otherwise
            returns the first match found. *Note*: the type annotations
            are unable to convey cases where this is not called with a
            literal `True` or `False` (as in when called with a boolean
            variable). Explicit type checking by the caller or ignoring
            the error is the only way to handle this scenario.

        Returns
        -------
        Union[Activity, List[Activity]]
            The name of the drs struct(s) that can be used to parse this path.

        Raises
        ------
        ValueError
            If `file_path` does not correspond with any DRS structure.
        """
        structures = []
        for path_prefix, st_type in DRSFile._get_structure_prefix_map().items():
            if file_path.startswith(path_prefix):
                if allow_multiples:
                    structures.append(st_type)
                else:
                    return st_type
        if not structures:
            raise ValueError(f"Unrecognized DRS structure in path {file_path}")
        else:
            return structures

    @staticmethod
    def find_structure_in_path(
        dir_path: str, allow_multiples: bool = False
    ) -> Union[Activity, list[Activity]]:
        """Return all DRS structures that might be applicable.

        See `find_structure_in_path` for more information

        Parameters
        ----------
        file_path
            Path to a directory which might contain DRS files.
        allow_multiples
            If true returns a list with all possible structures, otherwise
            returns the first match found.

        Returns
        -------
        Union[Activity, List[Activity]]
            The name of the drs struct(s) that can be used to parse this path.

        Raises
        ------
        ValueError
            If `dir_path` does not correspond with any DRS structure.
        """
        structures = []
        for path_prefix, st_type in DRSFile._get_structure_prefix_map().items():
            if dir_path.startswith(path_prefix):
                if allow_multiples:
                    structures.append(st_type)
                else:
                    return st_type
        if not structures:
            raise ValueError(f"No DRS structure found in {dir_path}.")
        else:
            return structures

    @staticmethod
    def from_path(path: str, activity: Optional[Activity] = None) -> DRSFile:
        """Extract a DRSFile object out of a path.

        Parameters
        ----------
        path
            Path to a file that is part of the ``drs_structure``.
        drs_structure
            Which structure is going to be used with this file.

        Returns
        -------
        DRSFile
            File extracted from path

        Raises
        ------
        ValueError
            If the given path cannot be used in the given DRS Structure
            or any configured structure if `activity` is None.
        """
        if activity is None:
            activity = DRSFile.find_structure_from_path(path)
        path = os.path.abspath(path)
        structure = DRSFile._get_drs_structure(activity)

        # trim root_dir
        if not path.startswith(structure.root_dir + os.sep):
            raise ValueError(f"File {path} does not correspond to {activity}")

        parts = path[len(structure.root_dir) + 1 :].split(os.sep)

        # check the number of parts
        if len(parts) != len(structure.parts_dir):
            raise ValueError(
                (
                    f"Can't parse this path. Expected {len(structure.parts_dir)} "
                    f"elements but got {len(parts)}."
                )
            )

        # first the dir
        result: FileComponents = {}
        result["root_dir"] = structure.root_dir
        result["parts"] = {}
        for i in range(len(structure.parts_dir)):
            result["parts"][structure.parts_dir[i]] = parts[i]

        # split file name
        # (extract .nc before splitting)
        # this type is technically incorrect. `split` would return a List[str] which is
        # not compatible with List[Optional[str]] but works here because mypy thinks
        # this returns Any anyway so it accepts whatever
        file_name_parts: list[Optional[str]] = result["parts"]["file_name"][:-3].split(
            "_"
        )  # type: ignore[assignment]
        if (
            len(file_name_parts) == len(structure.parts_file_name) - 1
            and "fx" in file_name_parts
        ):
            # no time
            file_name_parts.append(None)

        try:
            for i in range(len(structure.parts_file_name)):
                if structure.parts_file_name[i] not in result["parts"]:
                    result["parts"][structure.parts_file_name[i]] = file_name_parts[i]  # type: ignore [assignment]

        except IndexError:
            raise ValueError(
                f"File {path} does not follow the expected naming scheme for {activity}"
            )

        bl_file = DRSFile(result, drs_structure=activity)

        return bl_file

    def get_drs_structure(self) -> DRSStructure:
        """Returns the DRS structure used by this file.

        Returns
        -------
        DRSStructure
            The `DRS_STRUCTURE` used by this file."""
        return DRSFile._get_drs_structure(self.drs_structure)

    @staticmethod
    def _get_drs_structure(
        drs_structure: Activity = ACTIVITY_BASELINE0,
    ) -> DRSStructure:
        """Gets the DRSStructure associated with the given Activity

        Parameters
        ----------
        drs_structure
            Name of a DRS structure

        Returns
        -------
        DRSStructure
            The DRS structure of the requested type.

        Raises
        ------
        ValueError
            If there's no such DRS structure.
        """
        if DRSFile.DRS_STRUCTURE is None:
            DRSFile._load_structure_definitions()
        # these ignores are because mypy doesn't go into `_load_structure_definitions`
        # to see that DRS_STRUCTURE is initialized before being used and there isn't a
        # way to force that that wouldn't make the code much worse
        if drs_structure not in DRSFile.DRS_STRUCTURE:  # type: ignore [operator]
            raise ValueError(f"Unknown DRS structure {drs_structure}")
        return DRSFile.DRS_STRUCTURE[drs_structure]  # type: ignore [index]

    @staticmethod
    def from_dict(
        file_dict: FileComponents, drs_structure: Activity = ACTIVITY_BASELINE0
    ) -> DRSFile:
        """Creates a DRSFile based off given dict

        Parameters
        ----------
        file_dict
            Dictionary with the DRS components.
        drs_structure
            Name of a DRS structure

        Returns
        -------
        DRSFile
            The DRSFile generated from the given dictionary and DRS
            structure name
        """
        return DRSFile(file_dict, drs_structure=drs_structure)

    @staticmethod
    def from_json(
        json_str: str, drs_structure: Activity = ACTIVITY_BASELINE0
    ) -> DRSFile:
        """Creates a DRSFile based off the given JSON string.

        Parameters
        ----------
        json_str
            JSON representation of the DRS components. Like the result
            from calling :class:`DRSFile.to_json`.
        drs_structure
            Name of a DRS structure

        Returns
        -------
        DRSFile
            The DRSFile generated from the given dictionary and DRS
            structure name
        """
        return DRSFile.from_dict(json.loads(json_str), drs_structure=drs_structure)

    @staticmethod
    def solr_search(
        drs_structure: Optional[str] = None,
        latest_version: bool = True,
        path_only: bool = False,
        batch_size: int = 10000,
        **partial_dict: Any,
    ) -> Generator[Union[Any, DRSFile], None, None]:
        """Search for files by relying on a Solr Index.*'.

        Parameters
        ----------
        drs_structure
            Name of a DRS structure (key of :class:`DRSFile.DRS_STRUCTURE`). This isn't mandatory anymore.
        latest_version
            If this should be only the latest version available.
        path_only
            If true returns a string with the path only, otherwise a complete DRSFile object.
        batch_size
            The size of the number of results that will be returned by each Solr call.
        partial_dict
            A dictionary with some DRS components representing the query.

        Returns
        -------
        Generator[Union[Any, DRSFile], None, None]
            Generator returning matching files
        """
        from evaluation_system.model.solr import SolrFindFiles

        if drs_structure is not None:
            partial_dict["data_type"] = drs_structure
        if path_only:
            for path in SolrFindFiles.search(batch_size=batch_size, **partial_dict):
                yield path
        else:
            for path in SolrFindFiles.search(batch_size=batch_size, **partial_dict):
                yield DRSFile.from_path(path)

    @staticmethod
    def _load_structure_definitions() -> None:
        """Loads DRSStructure definitions from the config.

        This handles the initialization of `DRS_STRUCTURE_PATH_TYPE` and
        `DRS_STRUCTURE`.
        """
        DRSFile.DRS_STRUCTURE_PATH_TYPE = {}
        DRSFile.DRS_STRUCTURE = {}

        conf = config.get_drs_config()

        for a, structure in conf.items():
            activity = Activity(a)
            ds = DRSStructure.from_dict(structure)
            DRSFile.DRS_STRUCTURE[activity] = ds

            path_prefix = ds.root_dir
            for part in ds.parts_dir:
                # if we have more info use it to generate a unique root path
                # (e.g. cmip5 and baseline0 or baseline1 share the same root path!)
                if part in ds.defaults and all(
                    [char not in ds.defaults[part] for char in "*?"]
                ):
                    # but only use it if it's a plain string, no globing.
                    path_prefix += "/" + ds.defaults[part]
                else:
                    break
            DRSFile.DRS_STRUCTURE_PATH_TYPE[path_prefix] = activity
