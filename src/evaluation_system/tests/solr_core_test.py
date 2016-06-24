"""
Created on 23.05.2016

@author: Sebastian Illing
"""
import unittest
import tempfile
import os
import shutil

from evaluation_system.model.solr_core import SolrCore, META_DATA
from evaluation_system.model.solr import SolrFindFiles
from evaluation_system.model.file import DRSFile, CMIP5
from evaluation_system.misc import config
from evaluation_system.misc.utils import supermakedirs


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

    def tearDown(self):
        self.all_files.delete('*')
        self.latest.delete('*')
        unittest.TestCase.tearDown(self)

    def test_dump_to_file(self):
        tmpdir = tempfile.mkdtemp("_solr_core")

        files = ['cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc',
                 'cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc',
                 'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110719/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc']
        for f in files:
            abs_path = os.path.abspath(os.path.join(tmpdir, f))
            try:
                os.makedirs(os.path.dirname(abs_path))
            except:  # pragma nocover
                pass
            with open(abs_path, 'w') as f_out:
                f_out.write(' ')

        dump_file = tmpdir + '/dump1.csv'
        SolrCore.dump_fs_to_file(tmpdir + '/cmip5', dump_file)

        self.assertTrue(os.path.isfile(dump_file))
        dump_str = open(dump_file, 'r').read()
        self.assertTrue('%s\t%s' % (META_DATA.CRAWL_DIR, tmpdir) in dump_str)
        self.assertTrue(files[0] in dump_str)
        self.assertTrue(files[1] in dump_str)
        self.assertTrue(files[2] in dump_str)

        SolrCore.dump_fs_to_file(tmpdir + '/cmip5/output1/MOHC/HadCM3/historical', dump_file)

        self.assertTrue(os.path.isfile(dump_file))
        dump_str = open(dump_file, 'r').read()
        self.assertTrue('%s\t%s' % (META_DATA.CRAWL_DIR, tmpdir) in dump_str)
        self.assertTrue(files[0] in dump_str)
        self.assertTrue(files[1] not in dump_str)
        self.assertTrue(files[2] not in dump_str)

        # check gzipped creation
        dump_file += '.gz'
        SolrCore.dump_fs_to_file(tmpdir + '/cmip5', dump_file)
        self.assertTrue(os.path.isfile(dump_file))
        dump_gzip_header = open(dump_file, 'rb').read(2)
        gzip_header = '\037\213'
        self.assertEqual(dump_gzip_header, gzip_header)
        import gzip
        dump_str = gzip.open(dump_file, 'rb').read()
        self.assertTrue('%s\t%s' % (META_DATA.CRAWL_DIR, tmpdir) in dump_str)
        self.assertTrue(files[0] in dump_str)
        self.assertTrue(files[1] in dump_str)
        self.assertTrue(files[2] in dump_str)

        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)
            pass
        
    def test_ingest(self):
        supermakedirs('/tmp/some_temp_solr_core', 0777)
        tmpdir='/tmp/some_temp_solr_core'
        orig_dir = DRSFile.DRS_STRUCTURE[CMIP5]['root_dir']
        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = tmpdir

        files = ['cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc',
                 'cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc',
                 'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110719/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
                 'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
                 'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110419/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc']
        latest_versions = [files[0], files[1], files[3]]
        multiversion_latest = files[3]
        old_versions = [files[2], files[4]]

        for f in files:
            abs_path = os.path.abspath(os.path.join(tmpdir, f))
            try:
                os.makedirs(os.path.dirname(abs_path))
            except:  # pragma nocover
                pass
            with open(abs_path, 'w') as f_out:
                f_out.write(' ')

        dump_file = tmpdir + '/dump1.csv'
        SolrCore.dump_fs_to_file(tmpdir + '/cmip5', dump_file, check=True, abort_on_errors=True)
        # test instances, check they are as expected
        SolrCore.load_fs_from_file(dump_file, abort_on_errors=True,
                                   core_all_files=self.all_files, core_latest=self.latest)

        # check
        ff_all = SolrFindFiles(core='files', host=self.solr_host, port=self.solr_port)
        ff_latest = SolrFindFiles(core='latest', host=self.solr_host, port=self.solr_port)
        all_entries = [i for i in ff_all._search()]
        latest_entries = [i for i in ff_latest._search()]
        # old version should be only on the general core
        self.assertTrue(all([tmpdir + '/' + e in all_entries for e in files]))
        self.assertTrue(all([tmpdir + '/' + e in latest_entries for e in latest_versions]))
        self.assertTrue(all([tmpdir + '/' + e not in latest_entries for e in old_versions]))

        # add new version
        new_version = tmpdir + '/' + 'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20120419/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc'
        with open(dump_file, 'a') as f:
            f.write(new_version + ',1564083682.09\n')

        SolrCore.load_fs_from_file(dump_file, abort_on_errors=True,
                                   core_all_files=self.all_files, core_latest=self.latest)

        self.assertTrue(set(ff_all._search()).symmetric_difference(set(all_entries)).pop() == new_version)

        self.assertTrue((set(ff_latest._search()) - set(latest_entries)).pop() == new_version)
        self.assertTrue((set(latest_entries) - set(ff_latest._search())).pop() == tmpdir + '/' + multiversion_latest)

        # test get_solr_fields (facets)
        facets = self.all_files.get_solr_fields().keys()
        print self.all_files.get_solr_fields()
        facets_to_be = ['model', 'product', 'realm', 'version', 'data_type', 'institute', 'file_name', 'creation_time',
                        'cmor_table', 'time_frequency', 'experiment', 'timestamp', 'file', 'time', 'variable',
                        '_version_', 'file_no_version', 'project', 'ensemble']
        self.assertEqual(facets, facets_to_be)

        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = orig_dir
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)
            pass

    def test_reload(self):
        res = self.all_files.reload()
        self.assertEqual(['responseHeader'], res.keys())

    def test_unload_and_create(self):

        res = self.all_files.unload()
        status = self.all_files.status()
        self.assertEqual({}, status)
        self.all_files.create()
        self.assertEqual(len(self.all_files.status()), 9)

