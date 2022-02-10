"""
Created on 24.05.2016

@author: Sebastian Illing
"""
import os
from pathlib import Path
import pytest
import mock


def test_command(dummy_solr, capsys, temp_dir, admin_env):
    from evaluation_system.tests import run_cli
    from evaluation_system.model.solr import SolrFindFiles
    from evaluation_system.misc import config

    with mock.patch.dict(os.environ, admin_env, clear=True):
        with pytest.raises(SystemExit):
            run_cli(["solr", "foo"])
        assert "invalid choice" in capsys.readouterr().err
        run_cli(["solr", "index", dummy_solr.tmpdir])
        assert len(list(SolrFindFiles.search())) == 3
        assert len(list(SolrFindFiles.search(latest_version=False))) == 5
        run_cli(["solr", "index", dummy_solr.tmpdir, "--delete"])
        assert len(list(SolrFindFiles.search())) == 0
        assert len(list(SolrFindFiles.search(latest_version=False))) == 0


def test_forbidden_usage(capsys, dummy_env):
    from evaluation_system.tests import run_cli
    from freva.cli.admin import re_index, del_index

    with pytest.raises(SystemExit):
        run_cli(["solr", "index" "--help"])
    assert "invalid choice" in capsys.readouterr().err
    for func in (re_index, del_index):
        with pytest.raises(RuntimeError):
            func("foo")
