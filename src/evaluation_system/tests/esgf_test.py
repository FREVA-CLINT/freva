"""
Created on 30.05.2016

@author: Sebastian Illing
"""
import json
from pathlib import Path
import shlex

from evaluation_system.tests import run_cli


def test_show_facet(capsys, dummy_config):

    run_cli("esgf --show-facet=project,product -d")
    res = capsys.readouterr().out
    assert "[product]" in res
    assert "[project]" in res


def test_query(capsys, search_dict, dummy_config):
    from freva.cli.esgf import main as run

    run_cli("esgf --debug project=TEST --query=project,product --opendap")
    res = capsys.readouterr().out
    res = json.loads(res)[0]
    assert "project" in res.keys()
    run_cli("esgf -d project=TEST limit=1 --query=project --gridftp")
    res = capsys.readouterr().out
    assert "['TEST']" in res
    run(shlex.split("project=TEST --query=project --gridftp"))
    res = capsys.readouterr().out
    res = [r for r in res.split("\n") if r.strip()]
    num_res = len(res)
    run_cli("esgf project=TEST offset=1 --query=project --gridftp")
    res = capsys.readouterr().out
    res = [r for r in res.split("\n") if r.strip()]
    assert num_res == len(res) + 1
    run(["project=TESTs"])
    assert not capsys.readouterr().out
    run(shlex.split("project=TEST --datasets"))
    assert "- version:" in capsys.readouterr().out
    run(["--show-facet=blabla"])
    assert not capsys.readouterr().out


def test_freva_esgf_method(dummy_config):
    from freva import esgf

    result_to_be = [
        "output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/"
        "tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18500101-18591231.nc",
        "output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/"
        "tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18600101-18691231.nc",
    ]
    res = " ".join(
        esgf(
            project="CMIP5",
            experiment="historical",
            variable="tas",
            institute="MPI-M",
            time_frequency="day",
        )
    )
    for f in result_to_be:
        assert f in res
    res = esgf(show_facet="product")
    res = res["product"]["MRE2reanalysis"]
    assert res == 6
    fn = Path("/tmp/file_script.sh")
    res = esgf(
        project="CMIP5",
        model="MPI-ESM-LR",
        experiment="decadal2001",
        variable="tas",
        distrib=False,
        download_script=fn,
    )
    assert fn.is_file()
    assert res == f"Download script successfully saved to {fn}"
    assert oct(fn.stat().st_mode)[-3:] == "755"


def test_find_files(capsys, search_dict, dummy_config):

    result_to_be = [
        "output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/tas/1/"
        "tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc",
        "output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/"
        "tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc",
        "output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/"
        "tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc",
        "output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/"
        "tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc",
    ]

    run_cli("esgf --show-facet=blabla")
    assert not capsys.readouterr().out
    run_cli(["esgf"] + [f"{key}={val}" for key, val in search_dict.items()])
    res = capsys.readouterr().out
    for f in result_to_be:
        assert f in res
    run_cli(
        ["esgf"] + ["--datasets"] + [f"{key}={val}" for key, val in search_dict.items()]
    )
    res = capsys.readouterr().out
    assert (
        "cmip5.output1.MPI-M.MPI-ESM-LR.decadal2000.mon.atmos.Amon.r1i1p1 - version: 20120529"
        in res
    )


def test_download_script(capsys, search_dict, tmp_dir, dummy_config):

    fn = tmp_dir / "download_test_script.sh"
    run_cli(
        ["esgf"]
        + ["%s=%s" % (key, val) for key, val in search_dict.items()]
        + [f"--download-script={fn}"]
    )
    res = capsys.readouterr().out
    assert fn.is_file()
    assert res == f"Download script successfully saved to {fn}\n"
    assert oct(fn.stat().st_mode)[-3:] == "755"
