"""
Created on 31.05.2016

@author: Sebastian Illing
"""
import unittest
import os
import shutil

from evaluation_system.model.solr_core import SolrCore
from evaluation_system.model.solr import SolrFindFiles

from evaluation_system.misc import config
from evaluation_system.misc.utils import supermakedirs
from evaluation_system.model.file import DRSFile, CMIP5
from evaluation_system.model.file import DRSFile


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
            except:  # pragma nocover
                pass
            with open(abs_path, 'w') as f_out:
                f_out.write(' ')
        dump_file = self.tmpdir + '/dump1.csv'
        # add the files to solr
        SolrCore.dump_fs_to_file(self.tmpdir + '/cmip5', dump_file)
        SolrCore.load_fs_from_file(
            dump_file, abort_on_errors=True,
            core_all_files=self.all_files, core_latest=self.latest
        )

        self.fn = os.path.join(self.tmpdir, self.files[0])
        self.drs = DRSFile.from_path(self.fn)

    def tearDown(self):
        self.all_files.delete('*')
        self.latest.delete('*')

        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = self.orig_dir
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)
            pass

    def test_solr_search(self):

        # test path_only search
        res = DRSFile.solr_search(path_only=True, variable='tauu')
        self.assertEqual(list(res), [u'/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc'])

        # test drs search
        res = DRSFile.solr_search(variable='ua')
        for i in res:
            self.assertTrue(isinstance(i, DRSFile))

        # use drs_structure
        res = DRSFile.solr_search(drs_structure=CMIP5)
        for j, i in enumerate(res):
            self.assertTrue(isinstance(i, DRSFile))
        self.assertEqual(j+1, 3)

    def test_compare(self):
        fn2 = os.path.join(self.tmpdir, self.files[1])
        drs2 = DRSFile.from_path(fn2)

        self.assertTrue(self.drs == self.drs)
        self.assertFalse(self.drs == drs2)
        self.assertFalse(drs2 == fn2)

    def test_json_path(self):
        j = self.drs.to_json()
        self.assertTrue(isinstance(j, str))
        path = self.drs.to_path()
        self.assertEqual(path, self.fn)

    def test_find_structure_in_path(self):

        s = DRSFile.find_structure_in_path('/tmp/some_temp_solr_core/cmip5')
        self.assertEqual(s, 'cmip5')
        s = DRSFile.find_structure_in_path('/tmp/some_temp_solr_core/cmip5', allow_multiples=True)
        self.assertEqual(s, ['cmip5'])
        self.assertRaises(Exception, DRSFile.find_structure_in_path, '/no/valid/path')

    def test_structure_from_path(self):

        s = DRSFile.find_structure_from_path(self.fn)
        self.assertEqual(s,  'cmip5')
        s = DRSFile.find_structure_from_path(self.fn, allow_multiples=True)
        self.assertEqual(s, ['cmip5'])
        self.assertRaises(Exception, DRSFile.find_structure_from_path, '/no/valid/file_path')

    def test_from_dict(self):
        d = self.drs.dict
        t = DRSFile.from_dict(d, CMIP5)
        self.assertTrue(isinstance(t, DRSFile))
        self.assertEqual(self.drs.to_path(), t.to_path())

    def test_from_json(self):
        j = self.drs.to_json()
        t = DRSFile.from_json(j, CMIP5)
        self.assertTrue(isinstance(t, DRSFile))
        self.assertEqual(self.drs.to_path(), t.to_path())

    def test_to_dataset(self):
        res = self.drs.to_dataset_path(versioned=True)
        self.assertIn('/'.join(self.files[0].split('/')[:-1]), res)