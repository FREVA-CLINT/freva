"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import pytest


def test_crawl_my_data(dummy_crawl, capsys, dummy_env):
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
    assert _validate_user_dirs(root_path_str) == (root_path_with_empty_config,)
