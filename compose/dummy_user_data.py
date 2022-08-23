"""Python script that creates dummy user data."""
from __future__ import annotations
from pathlib import Path
from typing import Generator, Tuple

import cftime
import numpy as np
import xarray as xr


def create_data(
    temp_dir: Path,
    num_files: int,
    variable_names: list[str],
    chunk_size: Tuple[int, ...],
    dims: Tuple[str, ...],
) -> None:
    """Create a netcdf dataset."""
    coords = {d: np.ones(chunk_size[n]) for (n, d) in enumerate(dims)}
    data = xr.Dataset()
    attrs = {}
    ntstep = 0
    for nfile in range(num_files):
        if "time" in dims:
            units = "seconds since 1970-01-01 00:00:00"
            coords["time"] = cftime.num2date(
                np.array([ntstep + (j * 3600) for j in range(chunk_size[0])]),
                units=units,
            )
            data["time"] = xr.DataArray(
                data=coords["time"],
                dims=("time",),
                coords={"time": coords["time"]},
                name="time",
            )
            attrs["frequency"] = "not valid"
        for variable_name in variable_names:
            dset = xr.DataArray(
                np.zeros(chunk_size),
                dims=dims,
                coords=coords,
                name=variable_name,
            )
            data[variable_name] = dset
            out_f = Path(temp_dir) / f"outfile_{nfile}.nc"
            data.set_coords(dims).to_netcdf(str(out_f))
        ntstep += chunk_size[0] * 3600


if __name__ == "__main__":

    temp_dir = Path("/tmp/my_awesome_data/")
    temp_dir.mkdir(exist_ok=True, parents=True)
    create_data(
        temp_dir,
        10,
        ["tas", "time_bnds", "X", "rotated_pole", "longitude"],
        (10, 10, 10),
        ("time", "lat", "lon"),
    )
