"""The modules provides interfaces for userser to interact with 
the freva data stack."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Generator, Iterator, Union

import lazy_import
from evaluation_system.misc import config
from evaluation_system.misc.exceptions import ConfigurationException

xr = lazy_import.lazy_module("xarray")


class DataReader:
    """Read meta data facets from a collection of datafiles.

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

    def __init__(self, paths: os.PathLike, **defaults: str) -> None:

        self.paths = Path(paths)
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
        root_dir = (
            Path(config.get_drs_config()[DataReader.drs_specification]["root_dir"])
            .expanduser()
            .absolute()
        )
        return root_dir

    def __iter__(self) -> Generator[Path, None, None]:
        """Iterate over all found data files."""
        file_iter: Union[Iterator[Path], list[Path]] = []
        if self.paths.is_file():
            file_iter = [self.paths]
        elif self.paths.is_dir():
            file_iter = self.paths.rglob("*")
        else:
            # This is a shot into the dark assumes that the paths variable
            # is a glob pattern
            file_iter = self.paths.parent.rglob(self.paths.name)
        for file in file_iter:
            if file.suffix in self.suffixes:
                yield file

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
        return _data

    def file_name_from_metdata(self, path: os.PathLike) -> Path:
        """Construct file name matching the DRS Spec. from given input path.

        Parameters
        ----------
        path:
            Input file holing the meta data information.

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
            dir_path = self.root_dir.joinpath(*[meta_data[d] for d in self.parts_dir])
            file_path = self.file_sep.join([meta_data[d] for d in self.parts_file])
        except KeyError as error:
            raise ValueError(
                f"Not all information could be retrieved: {error}"
            ) from error

        out_dir = (dir_path / file_path).with_suffix(path.suffix)
        return out_dir
