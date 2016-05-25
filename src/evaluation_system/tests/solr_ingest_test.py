"""
Created on 24.05.2016

@author: Sebastian Illing
"""
import unittest
import os
import shutil

from evaluation_system.model.solr_core import SolrCore
from evaluation_system.model.solr import SolrFindFiles
from evaluation_system.tests.capture_std_streams import stdout
from evaluation_system.misc import config
from evaluation_system.misc.utils import supermakedirs
from evaluation_system.model.file import DRSFile, CMIP5
from evaluation_system.commands.admin.solr_ingest import Command
from evaluation_system.model.solr_models.models import UserCrawl


class Test(unittest.TestCase):
    def setUp(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        config.reloadConfiguration()
        self.solr_port = config.get('solr.port')
        self.solr_host = config.get('solr.host')
        # test instances, check they are as expected
        self.all_files = SolrCore(core='files', host=self.solr_host, port=self.solr_port)
        self.latest = SolrCore(core='latest', host=self.solr_host, port=self.solr_port)
        self.assertEquals(self.all_files.status()['index']['numDocs'], 0)
        self.assertEquals(self.latest.status()['index']['numDocs'], 0)

        # add some files to the cores
        supermakedirs('/tmp/some_temp_solr_core/', 0777)
        self.tmpdir = '/tmp/some_temp_solr_core'
        self.orig_dir = DRSFile.DRS_STRUCTURE[CMIP5]['root_dir']
        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = self.tmpdir

        self.files = [
            'cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110719/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110419/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc']
        for f in self.files:
            abs_path = os.path.abspath(os.path.join(self.tmpdir, f))
            try:
                os.makedirs(os.path.dirname(abs_path))
            except:
                pass
            with open(abs_path, 'w') as f_out:
                f_out.write(' ')
        self.cmd = Command()

    def tearDown(self):
        self.all_files.delete('*')
        self.latest.delete('*')
        UserCrawl.objects.all().delete()
        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = self.orig_dir
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)
            pass

    def test_command(self):

        with self.assertRaises(SystemExit):
            self.cmd.run([])

        with self.assertRaises(SystemExit):
            self.cmd.run(['--crawl=%s/cmip5' % self.tmpdir])

        # test crawl dir
        output = '/tmp/crawl_output.txt'
        self.cmd.run(['--crawl=%s/cmip5' % self.tmpdir, '--output=%s' % output])
        self.assertTrue(os.path.isfile(output))
        crawl_obj = UserCrawl.objects.get(tar_file=output.split('/')[-1])
        self.assertEqual(crawl_obj.status, 'crawling')
        # test ingesting
        self.assertEqual(len(list(SolrFindFiles.search())), 0)
        self.cmd.run(['--ingest=%s' % output])
        crawl_obj = UserCrawl.objects.get(tar_file=output.split('/')[-1])
        self.assertEqual(crawl_obj.status, 'success')
        self.assertEqual(len(list(SolrFindFiles.search())), 3)

        # test custom host and port
        self.cmd.run(['--ingest=%s' % output, '--solr-url=http://%s:%s' % (self.solr_host, self.solr_port)])
        self.assertEqual(len(list(SolrFindFiles.search(latest_version=False))), 5)

        os.remove(output)