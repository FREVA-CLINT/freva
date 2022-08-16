import shlex
import pytest

from evaluation_system.tests import run_cli


def test_index_len(dummy_solr):
    assert dummy_solr.all_files.status()["index"]["numDocs"] == 5
    assert dummy_solr.latest.status()["index"]["numDocs"] == 3


def test_time_subsets(dummy_solr):
    from freva import databrowser

    files = list(databrowser(project="cmip5"))
    subset_1 = databrowser(project="cmip5", time="2000-12 to 2012-12", count=True)
    subset_2 = databrowser(project="cmip5", time="1900 to 1918", count=True)
    subset_3 = databrowser(project="cmip5", time="2100", count=True)
    subset_4 = databrowser(
        project="cmip5", time="2000-12 to 2012-12", count=True, time_select="strict"
    )
    with pytest.raises(ValueError):
        databrowser(time="2000-12 to bar", count=True)
    assert subset_1 == 2
    assert subset_2 == 1
    assert subset_3 == 0
    assert subset_4 == 0
    with pytest.raises(ValueError):
        databrowser(time_select="bar")


def test_freva_databrowser_method(dummy_solr):
    from freva import databrowser

    all_files_output = sorted(
        [
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc",
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc",
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc",
        ]
    )
    res = list(databrowser(variable="ua"))
    assert res == [
        f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc"
    ]
    target = sorted(
        [
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc",
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc",
        ]
    )
    res = sorted(databrowser(variable=["ua", "tauu"]))
    assert res == target
    res = list(databrowser(variable=["ua", "tauu"], rows=1))
    assert len(res) == 1
    res = sorted(databrowser(variable=["ua", "tauu", "wetso2"]))
    assert res == all_files_output
    res = databrowser(variable=["ua", "tauu", "wetso2"], count=True)
    assert res == len(all_files_output)
    assert databrowser(variable="whhoop", count=True) == 0
    v = "v20110419"
    res = sorted(databrowser(variable="ua", version=v))
    assert v in res[0]
    with pytest.raises(TypeError):
        databrowser("badoption")
    res = databrowser(all_facets=True, relevant_only=True)
    assert isinstance(res, dict)
    target = sorted(
        [
            "cmor_table",
            "product",
            "realm",
            "dataset",
            "institute",
            "project",
            "time_frequency",
            "experiment",
            "variable",
            "model",
            "ensemble",
        ]
    )
    relevant = ["cmor_table", "ensemble", "experiment", "realm", "variable"]
    res = sorted(databrowser(attributes=True))
    assert sorted(target) == res
    res = sorted(databrowser(attributes=True, relevant_only=True))
    assert relevant == res


def test_search_files_cmd(dummy_solr, capsys):
    from evaluation_system.misc.exceptions import CommandError
    from freva.cli.databrowser import main as run

    cmd = shlex.split("databrowser")
    all_files_output = sorted(
        [
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc",
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc",
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc",
        ]
    )
    run_cli(cmd)
    res = sorted([f for f in capsys.readouterr().out.split("\n") if f])
    assert res == all_files_output
    run_cli(["databrowser", "--count"])
    res = capsys.readouterr().out.split("\n")
    assert int(res[0]) == len(all_files_output)
    run(["variable=whooop", "--count"])
    assert int(capsys.readouterr().out.split("\n")[0]) == 0
    run(["variable=ua"])
    res = capsys.readouterr().out
    assert (
        res
        == f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc\n"
    )
    res = run_cli(cmd + ["variable=ua", "variable=tauu"])
    res = capsys.readouterr().out
    target = sorted(
        [
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc",
            f"{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc",
        ]
    )
    res = sorted([f for f in sorted(res.split("\n")) if f])
    assert res == target
    run_cli(cmd + ["variable=ua", "variable=tauu", "variable=wetso2"])
    res = capsys.readouterr().out
    res = [f for f in sorted(res.split("\n")) if f]
    assert res == all_files_output
    # search specific version
    v = "v20110419"
    run_cli(cmd + ["variable=ua", f"version={v}"])
    res = capsys.readouterr().out
    assert v in res
    # test bad input
    with pytest.raises(ValueError):
        run_cli(cmd + ["badoption"])


def test_search_facets(dummy_solr, capsys):
    cmd = shlex.split("databrowser")
    all_facets = [
        map(str.strip, f.split(":"))
        for f in """cmor_table: aero,amon
product: output1
realm: aerosol,atmos
dataset: cmip5
institute: mohc
project: cmip5
time_frequency: mon
experiment: decadal2008,decadal2009,historical
variable: tauu,ua,wetso2
model: hadcm3
ensemble: r2i1p1,r7i2p1,r9i3p1
""".split(
            "\n"
        )
        if f
    ]
    run_cli(cmd + ["--all-facets"])
    res = capsys.readouterr().out
    res = [map(str.strip, f.split(":")) for f in res.split("\n") if f]
    assert dict(res) == dict(all_facets)
    all_facets = {
        "product": ["output1"],
        "realm": ["aerosol", "atmos"],
        "dataset": ["cmip5"],
        "institute": ["mohc"],
        "project": ["cmip5"],
        "time_frequency": ["mon"],
        "experiment": ["decadal2008", "decadal2009", "historical"],
        "variable": ["tauu", "ua", "wetso2"],
        "model": ["hadcm3"],
        "ensemble": ["r2i1p1", "r7i2p1", "r9i3p1"],
    }
    run_cli(cmd + ["--facet=variable"])
    res = capsys.readouterr().out
    assert res == "variable: tauu,ua,wetso2\n"
    run_cli(cmd + ["--facet=variable", "experiment=historical"])
    res = capsys.readouterr().out
    assert res == "variable: wetso2\n"
    run_cli(cmd + ["--facet=variable", "--facet-limit=2"])
    res = capsys.readouterr().out
    assert res == "variable: tauu,ua,...\n"
    run_cli(cmd + ["--facet=variable", "--count"])
    res = capsys.readouterr().out
    assert res == "variable: tauu (1),ua (1),wetso2 (1)\n"


def test_show_attributes(dummy_solr, capsys):

    cmd = shlex.split("databrowser --attributes")
    run_cli(cmd)
    res = capsys.readouterr().out
    res = sorted([f.strip() for f in res.split(",") if f])
    target = sorted(
        [
            "cmor_table",
            "product",
            "realm",
            "dataset",
            "institute",
            "project",
            "time_frequency",
            "experiment",
            "variable",
            "model",
            "ensemble",
        ]
    )
    assert target == res


def test_solr_backwards(dummy_solr, capsys):

    cmd = shlex.split("databrowser --all-facets")
    cmd += [
        f"file={dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc"
    ]
    run_cli(cmd)
    res = capsys.readouterr().out
    res = [map(str.strip, f.split(":")) for f in res.split("\n") if f]
    target = [
        map(str.strip, f.split(":"))
        for f in """cmor_table: amon
product: output1
realm: atmos
dataset: cmip5
institute: mohc
project: cmip5
time_frequency: mon
experiment: decadal2008
variable: tauu
model: hadcm3
ensemble: r9i3p1
""".split(
            "\n"
        )
        if f
    ]
    print(list(res))
    assert dict(res) == dict(target)
