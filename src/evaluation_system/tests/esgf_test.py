"""
Created on 30.05.2016

@author: Sebastian Illing
"""

import json
import shlex
from pathlib import Path

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
    assert "\n" in capsys.readouterr().out
    run(shlex.split("project=TEST --datasets"))
    assert "- version:" in capsys.readouterr().out
    run(["--show-facet=blabla"])
    assert not capsys.readouterr().out


def test_freva_esgf_method(dummy_config):
    from freva import esgf_browser, esgf_download, esgf_facets, esgf_query

    result_to_be = [
        "output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/"
        "tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18500101-18591231.nc",
        "output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/"
        "tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18600101-18691231.nc",
    ]
    res = " ".join(
        esgf_browser(
            project="CMIP5",
            experiment="historical",
            variable="tas",
            institute="MPI-M",
            time_frequency="day",
        )
    )
    for f in result_to_be:
        assert f in res
    result_to_be = [
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_201501010130-202412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_202501010130-203412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_203501010130-204412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_204501010130-205412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_205501010130-206412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_206501010130-207412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_207501010130-208412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_208501010130-209412312230.nc.html",
        "http://esgf3.dkrz.de/thredds/dodsC/cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_209501010130-210012312230.nc.html",
    ]
    res = " ".join(
        esgf_browser(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            frequency="3hr",
            variable="uas",
            variant_label="r1i1p1f2",
            distrib=False,
            latest=True,
            opendap=True,
        )
    )
    for f in result_to_be:
        assert f in res
    result_to_be = [
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_201501010130-202412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_202501010130-203412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_203501010130-204412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_204501010130-205412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_205501010130-206412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_206501010130-207412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_207501010130-208412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_208501010130-209412312230.nc",
        "gsiftp://esgf3.dkrz.de:2811//cmip6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp585/r1i1p1f2/E3hr/uas/gr/v20190219/uas_E3hr_CNRM-CM6-1_ssp585_r1i1p1f2_gr_209501010130-210012312230.nc",
    ]
    res = " ".join(
        esgf_browser(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            frequency="3hr",
            variable="uas",
            variant_label="r1i1p1f2",
            distrib=False,
            latest=True,
            gridftp=True,
        )
    )
    for f in result_to_be:
        assert f in res
    result_to_be = {
        "version": "20190219",
        "activity_id": ["ScenarioMIP"],
        "master_id": "CMIP6.ScenarioMIP.CNRM-CERFACS.CNRM-CM6-1.ssp585.r1i1p1f2.E3hr.vas.gr",
        "mip_era": ["CMIP6"],
        "product": ["model-output"],
        "source_id": ["CNRM-CM6-1"],
        "url": [
            "http://esgf3.dkrz.de/thredds/catalog/esgcet/1586/CMIP6.ScenarioMIP.CNRM-CERFACS.CNRM-CM6-1.ssp585.r1i1p1f2.E3hr.vas.gr.v20190219.xml#CMIP6.ScenarioMIP.CNRM-CERFACS.CNRM-CM6-1.ssp585.r1i1p1f2.E3hr.vas.gr.v20190219|application/xml+thredds|THREDDS",
            "http://esgf3.dkrz.de/las/getUI.do?catid=649F6BBCDD98B0633CF0042D119CC69D_ns_CMIP6.ScenarioMIP.CNRM-CERFACS.CNRM-CM6-1.ssp585.r1i1p1f2.E3hr.vas.gr.v20190219|application/las|LAS",
        ],
        "variable": ["vas"],
        "score": 1.0,
    }
    res = esgf_query(
        mip_era="CMIP6",
        activity_id="ScenarioMIP",
        source_id="CNRM-CM6-1",
        institution_id="CNRM-CERFACS",
        experiment_id="ssp585",
        frequency="3hr",
        variant_label="r1i1p1f2",
        distrib=False,
        latest=True,
        query=[
            "url",
            "master_id",
            "distribution",
            "mip_era",
            "activity_id",
            "source_id",
            "variable",
            "product",
            "version",
        ],
    )
    for key, value in result_to_be.items():
        if key in res[:1]:
            assert res[:1][key] == result_to_be[key]
    res = esgf_facets(show_facet="product")
    res = res["product"]["MRE2reanalysis"]
    assert res == 6
    fn = Path("/tmp/file_script.sh")
    res = esgf_download(
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
    res = esgf_download(
        project="CMIP5",
        model="MPI-ESM-LR",
        experiment="decadal2001",
        variable="tas",
        distrib=False,
    )
    fn = Path(res.split()[-1])
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
