"""The modules provides interfaces for user to interact with 
the freva data stack."""

from __future__ import annotations
from datetime import date
import os
from pathlib import Path
from typing import cast, Any, Collection, Generator, Iterator, Union

import lazy_import
from evaluation_system.misc import config
from evaluation_system.misc.exceptions import ConfigurationException

xr = lazy_import.lazy_module("xarray")


class DataReader:
    """Read meta data facets from a collection of data files.

    Parameters
    ----------
    paths: os.PathLike
        Input file or input directory of files containing the metadata.
    **defaults: str
        Any default facets that should be assigned.
    """

    suffixes: tuple[str, ...] = (".nc", ".nc4", ".grb", ".grib", ".zarr")
    """Allowed filetypes for files holding meta data."""

    file_sep: str = "_"
    """Character that separates facet values in the file name."""

    drs_specification: str = "crawl_my_data"
    """The drs holding metadata for user data information."""

    def __init__(
        self, paths: Union[os.PathLike, Collection[os.PathLike]], **defaults: str
    ) -> None:

        self.paths = paths
        self.defaults = defaults
        drs_config: dict[str, Any] = config.get_drs_config()[self.drs_specification]
        self.root_dir = Path(drs_config["root_dir"]).expanduser().absolute()
        self.parts_dir: list[str] = [
            d for d in drs_config["parts_dir"] if d != "file_name"
        ]
        self.parts_file: list[str] = drs_config["parts_file_name"]

    @staticmethod
    def get_output_directory() -> Path:
        """Get the user data output directory."""
        return get_output_directory()

    def __iter__(self) -> Generator[Path, None, None]:
        """Iterate over all found data files."""
        file_iter: Union[Iterator[os.PathLike], Collection[os.PathLike]] = []
        if isinstance(self.paths, (list, tuple, set)):
            file_iter = self.paths
        else:
            paths = Path(cast(os.PathLike, self.paths))
            if paths.is_file():
                file_iter = [paths]
            elif paths.is_dir():
                file_iter = paths.rglob("*")
            else:
                # This is a shot into the dark assumes that the paths variable
                # is a glob pattern
                file_iter = paths.parent.rglob(paths.name)
        for file in map(Path, file_iter):
            if file.suffix in self.suffixes:
                yield file.expanduser().absolute()

    @property
    def time_table(self) -> dict[int, str]:
        """Tranlatetion from seconds to cmor frequency."""
        return {
            315360000: "dec",
            31104000: "yr",
            2538000: "mon",
            1296000: "sem",
            84600: "day",
            21600: "6h",
            10800: "3h",
            3600: "hr",
            1: "subhr",
        }

    def _timedelta_to_cmor_frequency(self, dt: float) -> str:
        for total_seconds, frequency in self.time_table.items():
            if dt >= total_seconds:
                return frequency
        return "fx"

    def get_time_frequency(self, time_delta: int, freq_attr: str = "") -> str:
        """Create a comor time frequency facet.

        Parameters
        ----------
        time_delta: int
            time delta, in seconds, between consecutive time stpes.
        freq_attr: str, default: ""
            cmor time_frequency attribute that might already be in the data.

        Returns
        -------
        str:
            Matching cmor time frequency.
        """
        if freq_attr in list(self.time_table.values()):
            return freq_attr
        return self._timedelta_to_cmor_frequency(time_delta)

    def get_metadata(self, file_name: os.PathLike) -> dict[str, str]:
        """Read the metadata information from a given file.

        Parameters
        ----------
        file_name: os.PathLike
            The input file the meta data is read from.

        Returns
        -------
        dict[str, str]:
            Dictionary holding meta data information as key-value pair.

        Raises
        ------
        ValueError: If data could not be retrieved.
        """

        try:
            with xr.open_mfdataset(
                str(file_name), parallel=True, use_cftime=True
            ) as dset:
                time_freq = dset.attrs.get("frequency", "")
                data_vars = map(str, dset.data_vars)
                coords = map(str, dset.coords)
                try:
                    times = dset["time"].values[:]
                except (KeyError, IndexError, TypeError):
                    times = []
        except Exception as error:
            raise ValueError(
                f"Could not open data file {file_name}: {error}"
            ) from error
        if len(times) > 0:
            time_str = "-".join(
                [t.strftime("%Y%m%d%H%M") for t in (times[0], times[-1])]
            )
        else:
            time_str = "fx"
        if len(times) > 1:
            dt = abs((times[1] - times[0]).total_seconds())
        else:
            dt = 0
        variables: list[str] = []
        for var in data_vars:
            if var in coords:
                continue
            if (
                "lon" in var.lower()
                or "bnds" in var.lower()
                or "lat" in var.lower()
                or var.lower() in ("x", "y")
            ):
                # Usually those varaialbes should be flagged as coordinates
                # but we can't guaranty that they are.
                continue
            if var.lower() in ["rotated_pole", "rot_pole"]:
                # Also don't consider rotated pole variables
                continue
            variables.append(var)
        if len(variables) != 1:
            raise ValueError(f"Only one data variable allowed found: {variables}")
        _data = self.defaults.copy()
        _data.setdefault("variable", variables[0])
        _data.setdefault("time_frequency", self.get_time_frequency(dt, time_freq))
        _data["time"] = time_str
        _data.setdefault("cmor_table", _data["time_frequency"])
        _data.setdefault("version", "")
        return _data

    def _create_versioned_path(
        self, dir_parts: list[str], override: bool = True
    ) -> list[str]:
        """Add a version number to a file."""

        v_index = self.parts_dir.index("version")
        new_version = date.today().strftime("v%Y%m%d")
        version_path = self.root_dir.joinpath(*dir_parts[:v_index])
        try:
            versions = sorted([v.name for v in version_path.iterdir()])
        except FileNotFoundError:
            versions = [new_version]
        latest_version = [versions[-1]]
        new_dirs = dir_parts[:v_index] + latest_version + dir_parts[v_index:]
        new_path = self.root_dir.joinpath(*new_dirs)
        if new_path.is_dir() and not override:
            new_dirs[v_index] = new_version
        return new_dirs

    def file_name_from_metdata(self, path: os.PathLike, override: bool = False) -> Path:
        """Construct file name matching the DRS Spec. from given input path.

        Parameters
        ----------
        path:
            Input file holing the meta data information.
        override: bool, default: False
            If file exist, override the file instead of incrementing the version
            number.

        Returns
        -------
        os.PathLike:
            A file name matching the DRS sepcifications so that it can be
            ingested into the solr server.

        Raises
        ------
        ValueError:
            If data could not all metadata could be retrieved.
        """
        path = Path(path)
        meta_data = self.get_metadata(path)
        try:
            dir_parts = [meta_data[d] for d in self.parts_dir]
            file_parts = [meta_data[f] for f in self.parts_file]
        except KeyError as error:
            raise ValueError(
                "Not all information could be retrieved. "
                f"Please add the following key manually: {error}"
            ) from error
        if not meta_data["version"] and "version" in self.parts_dir:
            dir_parts = self._create_versioned_path(dir_parts, override=override)
        dir_path = self.root_dir.joinpath(*dir_parts)
        file_path = self.file_sep.join(file_parts)
        out_dir = (dir_path / file_path).with_suffix(path.suffix)
        return out_dir


def get_output_directory() -> Path:
    """Get the user data output directory."""
    root_dir = (
        Path(config.get_drs_config()[DataReader.drs_specification]["root_dir"])
        .expanduser()
        .absolute()
    )
    return root_dir
