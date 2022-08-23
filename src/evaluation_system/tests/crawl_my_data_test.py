"""Tests for ingesting user data."""
from __future__ import annotations
from pathlib import Path
import datetime
import mock
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


def test_invalid_data_files(invalid_data_files: Path, time_mock: mock_datetime) -> Path:
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


def test_add_valid_data(valid_data_files: Path, time_mock: mock_datetime) -> None:
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


def test_get_time_frequency(valid_data_files: Path, time_mock: mock_datetime) -> None:
    from evaluation_system.api.user_data import DataReader

    data_reader = DataReader(Path("foo/bar.nc"))
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


def test_get_file_name_from_metadata(
    valid_data_files: Path, time_mock: mock_datetime
) -> None:
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
    file_part = "foo/fumanshu/tong/mrfu/foo-boo/hr/foo-kingdom/foo/bar/v0/tas"
    assert file_part in str(data_reader.file_name_from_metdata(in_file).parent)
    defaults["variable"] = "foob"
    defaults["time_frequency"] = "3h"
    defaults.pop("cmor_table")
    data_reader = DataReader(valid_data_files, **defaults)
    file_part = "foo/fumanshu/tong/mrfu/foo-boo/3h/foo-kingdom/3h/bar/v0/foob"
    assert file_part in str(data_reader.file_name_from_metdata(in_file).parent)
    defaults.pop("version")
    data_reader = DataReader(valid_data_files, **defaults)
    file_part = "foo/fumanshu/tong/mrfu/foo-boo/3h/foo-kingdom/3h/bar/v19990909/foob"
    assert file_part in str(data_reader.file_name_from_metdata(in_file).parent)
    defaults.pop("ensemble")
    data_reader = DataReader(valid_data_files, **defaults)
    with pytest.raises(ValueError):
        data_reader.file_name_from_metdata(in_file)


def test_versions(valid_data_files: Path, time_mock: mock_datetime) -> None:
    def get_new_file(inp: Path, override: bool = False) -> Path:
        defaults = dict(
            project="foo",
            product="fumanshu",
            institute="tong",
            model="mrfu",
            experiment="foo-boo",
            cmor_table="foo",
            ensemble="bar",
            realm="foo-kingdom",
        )
        from evaluation_system.api.user_data import DataReader

        data_reader = DataReader(inp, **defaults)
        return data_reader.file_name_from_metdata(inp, override=override)

    in_file = list(valid_data_files.rglob("*.*"))[0]
    new_file = get_new_file(in_file)
    assert "v19990909" in str(new_file)
    new_file.parent.mkdir(exist_ok=True, parents=True)
    new_file.touch()
    time_mock._day = 10
    new_file2 = get_new_file(in_file)
    new_file2.parent.mkdir(exist_ok=True, parents=True)
    new_file2.touch()
    new_file3 = get_new_file(in_file, override=False)
    assert new_file != new_file2
    assert new_file3 == new_file2


def test_iter_data_files(valid_data_files: Path, time_mock: mock_datetime) -> None:
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


def test_link_my_data(dummy_crawl, dummy_plugin, valid_data_files, time_mock):

    import freva

    input_files = list(valid_data_files.rglob("*.nc"))
    dummy_plugin.add_output_to_databrowser(
        valid_data_files, "muh", "mah", experiment="foo"
    )
    assert len(list(freva.databrowser(experiment="foo"))) == len(input_files)
    assert len(list(freva.databrowser(product="muh.mah"))) == len(input_files)


def test_add_my_data(valid_data_files, time_mock):

    from freva import UserData, databrowser
    from freva.cli.user_data import main as run

    defaults = [
        "--institute",
        "tong",
        "--model",
        "mrfu",
        "--experiment",
        "foo-boo",
        "--cmor_table",
        "foo",
        "--ensemble",
        "bar",
        "--realm",
        "foo-kingdom",
    ]
    run(["add", "foo-product", str(valid_data_files)] + defaults)
    run(["add", "foo-product", str(valid_data_files)] + defaults + ["--override"])
    input_files = list(valid_data_files.rglob("*.nc"))
    with pytest.raises(SystemExit):
        run(["add", "foo-product", str(valid_data_files)])
    with pytest.raises(ValueError):
        run(["add", "foo-product", str(valid_data_files), "-d"])

    user_data = UserData()
    assert databrowser(product="foo-product", count=True) == len(input_files)
    with pytest.raises(ValueError):
        user_data.add("foo-product", valid_data_files, how="foo")
    with pytest.warns(UserWarning):
        user_data.add("foo-product")


def test_add_methods():

    from freva import UserData
    import shutil
    import os

    assert UserData._set_add_method("cp") == shutil.copy
    assert UserData._set_add_method("mv") == shutil.move
    assert UserData._set_add_method("ln") == os.symlink
    assert UserData._set_add_method("link") == os.link
    with pytest.raises(ValueError):
        UserData._set_add_method("foo")


def test_delete_my_data(valid_data_files, time_mock):

    import freva
    from freva import UserData
    from freva.cli.user_data import main as run
    from evaluation_system.model.user import User
    from evaluation_system.api.user_data import get_output_directory

    user_data = UserData()
    root_path = get_output_directory() / f"user-{User().getName()}" / "foo-product"
    assert freva.databrowser(product="foo-product", count=True) > 0
    nfiles = len(list(root_path.rglob("*.nc")))
    assert nfiles > 0
    run(["delete", str(root_path)])
    assert freva.databrowser(product="foo-product", count=True) == 0
    assert len(list(root_path.rglob("*.nc"))) > 0
    user_data.delete(root_path, delete_from_fs=True)
    assert len(list(root_path.rglob("*.nc"))) == 0


def test_index_my_data(dummy_crawl, capsys, dummy_env, valid_data_files, time_mock):
    from freva import UserData
    from evaluation_system.tests import run_cli
    from freva.cli.user_data import main as run
    from evaluation_system.misc.exceptions import ValidationError
    from evaluation_system.model.solr import SolrFindFiles

    run(["index", "--data-type=fs", "-d"])
    captured = capsys.readouterr()
    assert "Status: crawling ..." in captured.out
    assert "ok" in captured.out
    assert len(list(SolrFindFiles.search(product="foo"))) == len(dummy_crawl) - 2
    assert len(list(SolrFindFiles.search(product="foo", latest_version=False))) == len(
        dummy_crawl
    )
    user_data = UserData()
    with pytest.raises(NotImplementedError):
        user_data.index(dtype="something")
    with pytest.raises(SystemExit):
        with pytest.raises(ValidationError):
            run_cli(["user-data", "index", "/tmp/forbidden/folder"])


def test_wrong_datatype(dummy_crawl, capsys, dummy_env, time_mock):

    from evaluation_system.tests import run_cli
    from evaluation_system.model.solr import SolrFindFiles

    dummy_crawl.append(dummy_crawl[0].parent / "more_info" / dummy_crawl[0].name)
    dummy_crawl[-1].parent.mkdir(exist_ok=True, parents=True)
    dummy_crawl[-1].touch()
    with pytest.raises(ValueError):
        run_cli(["user-data", "index", "-d"])
    with pytest.raises(SystemExit):
        run_cli(["user-data", "index"])
    captured = capsys.readouterr()
    assert "ValueError" in captured.err
    assert len(list(SolrFindFiles.search())) == 0
    assert len(list(SolrFindFiles.search(latest_version=False))) == 0


def test_validate_path(root_path_with_empty_config, time_mock):
    from freva import UserData

    user_data = UserData()
    root_path_str = str(root_path_with_empty_config)
    print(root_path_str)
    assert user_data._validate_user_dirs(root_path_str) == (
        root_path_with_empty_config,
    )
