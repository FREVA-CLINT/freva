"""
Created on 24.05.2016

@author: Sebastian Illing
"""
from copy import deepcopy
from pathlib import Path
import os

import pytest




def test_command(dummy_crawl, stdout, temp_dir, dummy_settings):
    from evaluation_system.commands.admin.solr_ingest import Command
    from evaluation_system.model.solr_models.models import UserCrawl
    from evaluation_system.model.solr import SolrFindFiles
    cmd = Command()
    with pytest.raises(SystemExit):
        cmd.run([])

    with pytest.raises(SystemExit):
        cmd.run(['--crawl=%s/cmip5' % dummy_crawl.tmpdir])
    # test crawl dir
    output = Path(temp_dir) / 'crawl_output.txt'
    cmd.run(['--crawl=%s/cmip5' % dummy_crawl.tmpdir, '--output=%s' % output])
    crawl_obj = UserCrawl.objects.get(tar_file=output.name)
    assert crawl_obj.status == 'crawling'
    # test ingesting
    assert len(list(SolrFindFiles.search())) == 0
    cmd.run(['--ingest=%s' % output])
    crawl_obj = UserCrawl.objects.get(tar_file=output.name)
    assert crawl_obj.status == 'success'
    assert len(list(SolrFindFiles.search())) == 3

    # test custom host and port
    cmd.run(['--ingest=%s' % output,
                 f'--solr-url=http://{dummy_crawl.solr_host}:{dummy_crawl.solr_port}'
                 ])
    assert len(list(SolrFindFiles.search(latest_version=False))) == 5
