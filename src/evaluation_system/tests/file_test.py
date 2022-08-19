"""
Created on 31.05.2016

@author: Sebastian Illing
"""
import os
from pathlib import Path
import pytest
import shutil


def test_solr_search(dummy_solr):
    from evaluation_system.model.file import DRSFile

    # test path_only search
    res = dummy_solr.DRSFile.solr_search(path_only=True, variable="tauu")
    assert list(res) == [str(Path(dummy_solr.tmpdir) / dummy_solr.files[1])]

    # test drs search
    res = dummy_solr.DRSFile.solr_search(variable="ua")
    for i in res:
        assert isinstance(i, DRSFile)

    # use drs_structure
    res = dummy_solr.DRSFile.solr_search(drs_structure="cmip5")
    for j, i in enumerate(res):
        assert isinstance(i, DRSFile)
    assert j + 1 == 3


def test_compare(dummy_solr):
    fn2 = os.path.join(dummy_solr.tmpdir, dummy_solr.files[1])
    drs2 = dummy_solr.DRSFile.from_path(fn2)

    assert dummy_solr.drs == dummy_solr.drs
    assert not (dummy_solr.drs == drs2)
    assert not (drs2 == fn2)


def test_json_path(dummy_solr):
    j = dummy_solr.drs.to_json()
    assert isinstance(j, str)
    path = dummy_solr.drs.to_path()
    assert path == dummy_solr.fn


def test_find_structure_in_path(dummy_solr):

    search_path = str(Path(dummy_solr.tmpdir) / "cmip5")
    s = dummy_solr.DRSFile.find_structure_in_path(search_path)
    assert s == "cmip5"
    s = dummy_solr.DRSFile.find_structure_in_path(search_path, allow_multiples=True)
    assert s == ["cmip5"]
    with pytest.raises(ValueError):
        dummy_solr.DRSFile.find_structure_in_path("/no/valid/path")


def test_structure_from_path(dummy_solr):

    s = dummy_solr.DRSFile.find_structure_from_path(dummy_solr.fn)
    assert s == ["cmip5"]
    s = dummy_solr.DRSFile.find_structure_from_path(dummy_solr.fn, allow_multiples=True)
    assert s == ["cmip5"]
    with pytest.raises(ValueError):
        dummy_solr.DRSFile.find_structure_from_path("/no/valid/file_path")


def test_from_dict(dummy_solr):
    d = dummy_solr.drs.dict
    t = dummy_solr.DRSFile.from_dict(d, "cmip5")
    assert isinstance(t, dummy_solr.DRSFile)
    assert dummy_solr.drs.to_path() == t.to_path()


def test_from_json(dummy_solr):
    j = dummy_solr.drs.to_json()
    t = dummy_solr.DRSFile.from_json(j, "cmip5")
    assert isinstance(t, dummy_solr.DRSFile)
    assert dummy_solr.drs.to_path() == t.to_path()


def test_to_dataset(dummy_solr, dummy_reana):
    from evaluation_system.model.file import DRSFile

    res = Path(dummy_solr.drs.to_dataset_path(versioned=True))
    root_dir = Path(dummy_solr.drs.dict["root_dir"])
    file = root_dir / Path(dummy_solr.files[0]).parent
    assert file == res
    drs = DRSFile.from_path(dummy_reana[0])
    res = Path(drs.to_dataset_path(versioned=False))
    assert Path(dummy_reana[0]).parent == res
    with pytest.raises(ValueError):
        drs.to_dataset_path(versioned=True)
