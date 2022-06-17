"""Tests for ingesting user data."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from typing import Generator, Tuple

import cftime
import pytest
import numpy as np
import xarray as xr


def create_data(
    num_files: int,
    variable_names: list[str],
    chunk_size: Tuple[int, ...],
    dims: Tuple[str, ...],
) -> Generator[Path, None, None]:
    """Create a netcdf dataset."""
    coords = {d: np.ones(chunk_size[n]) for (n, d) in enumerate(dims)}
    data = xr.Dataset()
    attrs = {}
    ntstep = 0
    with TemporaryDirectory() as temp_dir:
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
        yield Path(temp_dir)


@pytest.fixture(scope="function")
def valid_data_files() -> Generator[Path, None, None]:
    yield from create_data(
        10,
        ["tas", "time_bnds", "X", "rotated_pole", "longitude"],
        (10, 10, 10),
        ("time", "lat", "lon"),
    )


@pytest.fixture(scope="function")
def invalid_data_files() -> Generator[Path, None, None]:
    yield from create_data(1, ["tas", "foo"], (10, 10), ("lat", "lon"))


def test_invalid_data_files(invalid_data_files: Path) -> Path:
    from evaluation_system.api.user_data import DataReader

    in_file = list(invalid_data_files.rglob("*.*"))[0]
    data_reader = DataReader(invalid_data_files)
    with pytest.raises(ValueError):
        data_reader.get_metadata(in_file)
    not_a_nc_file = invalid_data_files / "not_a_nc_file.nc"
    not_a_nc_file.touch()
    data_reader = DataReader(not_a_nc_file)
    with pytest.raises(ValueError):
        data_reader.get_metadata(not_a_nc_file)


def test_add_valid_data(valid_data_files: Path) -> None:
    from evaluation_system.api.user_data import DataReader

    in_file = list(valid_data_files.rglob("*.*"))[0]
    data_reader = DataReader(valid_data_files)
    data = data_reader.get_metadata(in_file)
    assert data["variable"] == "tas"
    assert data["time_frequency"] == "hr"
    data_reader = DataReader(valid_data_files, variable="foo")
    data = data_reader.get_metadata(in_file)
    assert data["variable"] == "foo"
    assert data["time_frequency"] == "hr"
    with xr.open_dataset(str(in_file)) as dset:
        dset = dset.isel(time=0).load()
    dset.to_netcdf(in_file)
    data = data_reader.get_metadata(in_file)
    assert data["variable"] == "foo"
    assert data["time_frequency"] == "fx"


def test_get_time_frequency(valid_data_files: Path) -> None:
    from evaluation_system.api.user_data import DataReader

    data_reader = DataReader("foo/bar.nc")
    hour = 3600
    day = hour * 24
    mon = day * 30
    year = day * 360
    assert data_reader.get_time_frequency(0, "foo") == "fx"
    assert data_reader.get_time_frequency(0, "hr") == "hr"
    assert data_reader.get_time_frequency(60) == "subhr"
    assert data_reader.get_time_frequency(hour) == "hr"
    assert data_reader.get_time_frequency(day) == "day"
    assert data_reader.get_time_frequency(15 * day) == "sem"
    assert data_reader.get_time_frequency(mon) == "mon"
    assert data_reader.get_time_frequency(year) == "yr"


def test_get_file_name_from_metadata(valid_data_files: Path) -> None:
    from evaluation_system.api.user_data import DataReader

    in_file = list(valid_data_files.rglob("*.*"))[0]
    defaults = dict(
        project="foo",
        product="fumanshu",
        institute="tong",
        model="mrfu",
        experiment="foo-boo",
        cmor_table="foo",
        ensemble="bar",
        realm="foo-kingdom",
        version="v0",
    )
    data_reader = DataReader(valid_data_files, **defaults)
    file_part = "foo/fumanshu/tong/mrfu/foo-boo/hr/foo-kingdom/foo/bar/tas"
    assert file_part in str(data_reader.file_name_from_metdata(in_file).parent)
    defaults["variable"] = "foob"
    defaults["time_frequency"] = "3h"
    data_reader = DataReader(valid_data_files, **defaults)
    file_part = "foo/fumanshu/tong/mrfu/foo-boo/3h/foo-kingdom/foo/bar/foob"
    assert file_part in str(data_reader.file_name_from_metdata(in_file).parent)
    defaults.pop("cmor_table")
    data_reader = DataReader(valid_data_files, **defaults)
    with pytest.raises(ValueError):
        data_reader.file_name_from_metdata(in_file)


def test_iter_data_files(valid_data_files: Path) -> None:
    from evaluation_system.api.user_data import DataReader

    input_files = list(valid_data_files.rglob("*.*"))
    not_a_nc_file = valid_data_files / "not_a_nc_file.txt"
    not_a_nc_file.touch()
    data_reader = DataReader(valid_data_files)
    files = [f for f in data_reader]
    data_reader = DataReader(valid_data_files / "*.nc")
    files = [f for f in data_reader]
    assert len(files) == len(input_files)
    data_reader = DataReader(valid_data_files / "*.txt")
    files = [f for f in data_reader]
    assert files == []
    data_reader = DataReader(not_a_nc_file)
    files = [f for f in data_reader]
    assert files == []


def test_link_my_data(dummy_crawl, dummy_plugin, valid_data_files):

    from evaluation_system.model.solr import SolrFindFiles

    input_files = list(valid_data_files.rglob("*.nc"))
    dummy_plugin.add_output_to_databrowser(valid_data_files)
    assert len(list(SolrFindFiles.search(latest_version=False))) == len(input_files)


def test_crawl_my_data(dummy_crawl, capsys, dummy_env, valid_data_files):
    from freva import crawl_my_data
    from evaluation_system.tests import run_cli
    from freva.cli.crawl_my_data import main as run
    from evaluation_system.misc.exceptions import ValidationError
    from evaluation_system.model.solr import SolrFindFiles

    run(["--data-type=fs"])
    captured = capsys.readouterr()
    assert "Status: crawling ..." in captured.out
    assert "ok" in captured.out
    assert len(list(SolrFindFiles.search())) == len(dummy_crawl)
    assert len(list(SolrFindFiles.search(latest_version=False))) == len(dummy_crawl)
    with pytest.raises(NotImplementedError):
        crawl_my_data(dtype="something")
    with pytest.raises(SystemExit):
        with pytest.raises(ValidationError):
            run_cli(["crawl-my-data", "/tmp/forbidden/folder"])


def test_wrong_datatype(dummy_crawl, capsys, dummy_env):

    from evaluation_system.tests import run_cli
    from evaluation_system.model.solr import SolrFindFiles

    dummy_crawl.append(dummy_crawl[0].parent / "more_info" / dummy_crawl[0].name)
    dummy_crawl[-1].parent.mkdir(exist_ok=True, parents=True)
    dummy_crawl[-1].touch()
    with pytest.raises(ValueError):
        run_cli(["crawl-my-data", "-d"])
    with pytest.raises(SystemExit):
        run_cli(["crawl-my-data"])
    captured = capsys.readouterr()
    assert "ValueError" in captured.err
    assert len(list(SolrFindFiles.search())) == 0
    assert len(list(SolrFindFiles.search(latest_version=False))) == 0


def test_validate_path(root_path_with_empty_config):
    from freva._crawl_my_data import _validate_user_dirs

    root_path_str = str(root_path_with_empty_config)
    print(root_path_str)
    assert _validate_user_dirs(root_path_str) == (root_path_with_empty_config,)
