"""
Created on 24.05.2016

@author: Sebastian Illing
"""
import os


def test_solr_search(dummy_solr):
    # search some files
    from evaluation_system.model.solr import SolrFindFiles

    solr_search = SolrFindFiles()
    all_files = solr_search.search()
    assert len(list(all_files)) == 3
    hist = solr_search.search(experiment="historical")
    assert list(hist) == [os.path.join(dummy_solr.tmpdir, dummy_solr.files[0])]
    all_files = solr_search.search(latest_version=False)
    assert len(list(all_files)) == 5
    # test OR query
    or_result = solr_search.search(variable=["tauu", "wetso2"])
    assert set(
        [os.path.join(dummy_solr.tmpdir, e) for e in dummy_solr.files[:2]]
    ) == set(or_result)


def test_facet_search(dummy_solr):

    from evaluation_system.model.solr import SolrFindFiles

    factes_to_be = {
        "cmor_table": ["aero", 1, "amon", 2],
        "product": ["output1", 3],
        "realm": ["aerosol", 1, "atmos", 2],
        "dataset": ["cmip5", 3],
        "institute": ["mohc", 3],
        "project": ["cmip5", 3],
        "time_frequency": ["mon", 3],
        "experiment": ["decadal2008", 1, "decadal2009", 1, "historical", 1],
        "variable": ["tauu", 1, "ua", 1, "wetso2", 1],
        "model": ["hadcm3", 3],
        "ensemble": ["r2i1p1", 1, "r7i2p1", 1, "r9i3p1", 1],
    }
    s = SolrFindFiles
    all_factes = s.facets()
    assert len(all_factes) == 11
    assert all_factes == factes_to_be

    var_facets = s.facets(facets=["variable"])
    assert var_facets == dict(variable=factes_to_be["variable"])
    experiment_facets = s.facets(facets="experiment", cmor_table="amon")
    assert experiment_facets == {"experiment": ["decadal2008", 1, "decadal2009", 1]}

    # test files core
    res = s.facets(facets="variable,project", latest_version=False)
    assert list(res.keys()) == ["variable", "project"]
    assert res == {
        "variable": ["tauu", 1, "ua", 3, "wetso2", 1],
        "project": ["cmip5", 5],
    }
