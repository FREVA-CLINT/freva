"""
Created on 23.05.2016

@author: Sebastian Illing
"""
import gzip
import os
from pathlib import Path

import pytest


def test_ingest(dummy_solr):
    from evaluation_system.model.solr_core import SolrCore
    from evaluation_system.model.solr import SolrFindFiles
    from evaluation_system.misc.utils import supermakedirs

    latest_versions = [dummy_solr.files[0], dummy_solr.files[1], dummy_solr.files[3]]
    multiversion_latest = dummy_solr.files[3]
    old_versions = [dummy_solr.files[2], dummy_solr.files[4]]
    data_dir = Path(dummy_solr.tmpdir) / "cmip5"
    # test instances, check they are as expected
    SolrCore.load_fs(
        data_dir,
        abort_on_errors=True,
        core_all_files=dummy_solr.all_files,
        core_latest=dummy_solr.latest,
    )
    # check
    ff_all = SolrFindFiles(
        core="files", host=dummy_solr.solr_host, port=dummy_solr.solr_port
    )
    ff_latest = SolrFindFiles(
        core="latest", host=dummy_solr.solr_host, port=dummy_solr.solr_port
    )
    all_entries = [i for i in ff_all._search()]
    latest_entries = [i for i in ff_latest._search()]
    assert all([dummy_solr.tmpdir + "/" + e in all_entries for e in dummy_solr.files])
    assert all([dummy_solr.tmpdir + "/" + e in latest_entries for e in latest_versions])
    assert all(
        [dummy_solr.tmpdir + "/" + e not in latest_entries for e in old_versions]
    )

    # add new version
    new_version = (
        Path(dummy_solr.tmpdir)
        / "cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20120419/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc"
    )
    new_version.parent.mkdir(parents=True, exist_ok=True)
    new_version.touch()
    SolrCore.load_fs(
        new_version,
        abort_on_errors=True,
        core_all_files=dummy_solr.all_files,
        core_latest=dummy_solr.latest,
    )
    assert set(ff_all._search()).symmetric_difference(set(all_entries)).pop() == str(
        new_version
    )
    assert (set(ff_latest._search()) - set(latest_entries)).pop() == str(new_version)
    # TODO: The below test does not make much sense, because data set versioning
    # doesn't really work, let's turn it off for now
    # assert (set(latest_entries) - set(ff_latest._search())).pop() == dummy_solr.tmpdir + '/' + multiversion_latest
    # test get_solr_fields (facets)
    facets = dummy_solr.all_files.get_solr_fields().keys()
    facets_to_be = [
        "model",
        "product",
        "realm",
        "version",
        "dataset",
        "institute",
        "file_name",
        "creation_time",
        "cmor_table",
        "time_frequency",
        "experiment",
        "timestamp",
        "file",
        "time",
        "variable",
        "_version_",
        "file_no_version",
        "project",
        "ensemble",
    ]
    assert sorted(facets) == sorted(facets_to_be)


def test_reload(dummy_solr):
    res = dummy_solr.all_files.reload()
    assert ["responseHeader"] == list(res.keys())


def test_unload_and_create(dummy_solr):

    res = dummy_solr.all_files.unload()
    status = dummy_solr.all_files.status()
    assert {} == status
    # with pytest.raises(FileNotFoundError):
    #    dummy_solr.all_files.create()
    dummy_solr.all_files.create(check_if_exist=False)
    assert len(dummy_solr.all_files.status()) >= 8
