"""
Created on 24.05.2016

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

    def tearDown(self):
        self.all_files.delete('*')
        self.latest.delete('*')

        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = self.orig_dir
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)
            pass

    def test_solr_search(self):
        # search some files
        solr_search = SolrFindFiles()
        all_files = solr_search.search()
        self.assertEqual(len(list(all_files)), 3)
        hist = solr_search.search(experiment='historical')
        self.assertEqual(list(hist), [os.path.join(self.tmpdir, self.files[0])])
        all_files = solr_search.search(latest_version=False)
        self.assertEqual(len(list(all_files)), 5)
        # test OR query
        or_result = solr_search.search(variable=['tauu', 'wetso2'])
        self.assertEqual(set([os.path.join(self.tmpdir, e) for e in self.files[:2]]), set(or_result))

    def test_facet_search(self):

        factes_to_be = {'cmor_table': ['aero', 1, 'amon', 2], 'product': ['output1', 3],
                        'realm': ['aerosol', 1, 'atmos', 2], 'data_type': ['cmip5', 3],
                        'institute': ['mohc', 3], 'project': ['cmip5', 3], 'time_frequency': ['mon', 3],
                        'experiment': ['decadal2008', 1, 'decadal2009', 1, 'historical', 1],
                        'variable': ['tauu', 1, 'ua', 1, 'wetso2', 1], 'model': ['hadcm3', 3],
                        'ensemble': ['r2i1p1', 1, 'r7i2p1', 1, 'r9i3p1', 1]}
        s = SolrFindFiles
        all_factes = s.facets()
        self.assertEqual(len(all_factes), 11)
        self.assertEqual(all_factes, factes_to_be)

        var_facets = s.facets(facets=['variable'])
        self.assertEqual(var_facets, dict(variable=factes_to_be['variable']))
        experiment_facets = s.facets(facets='experiment', cmor_table='amon')
        self.assertEqual(experiment_facets, {'experiment': ['decadal2008', 1, 'decadal2009', 1]})

        # test files core
        res = s.facets(facets='variable,project', latest_version=False)
        self.assertEqual(res.keys(), ['variable', 'project'])
        self.assertEqual(res, {'variable': ['tauu', 1, 'ua', 3, 'wetso2', 1], 'project': ['cmip5', 5]})