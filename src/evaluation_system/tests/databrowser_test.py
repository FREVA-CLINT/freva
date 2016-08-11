"""
Created on 25.05.2016

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
from evaluation_system.commands.databrowser import Command
from evaluation_system.commands.basecommand import CommandError
from evaluation_system.tests.capture_std_streams import stdout


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

        self.cmd = Command()

    def tearDown(self):
        self.all_files.delete('*')
        self.latest.delete('*')

        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = self.orig_dir
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)
            pass

    def run_command_with_capture(self, args_list=[]):

        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(args_list)
        stdout.stopCapturing()
        return stdout.getvalue()

    def test_search_files(self):

        all_files_output = u'''/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc
/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc
/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc
'''
        res = self.run_command_with_capture()
        self.assertEqual(res, all_files_output)

        res = self.run_command_with_capture(['variable=ua'])
        self.assertEqual(res, '/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc\n')

        res = self.run_command_with_capture(['variable=ua', 'variable=tauu'])
        self.assertEqual(res, """/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc\n/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc\n""")

        res = self.run_command_with_capture(['variable=ua', 'variable=tauu', 'variable=wetso2'])
        self.assertEqual(res, all_files_output)

        # search specific version
        v = 'v20110419'
        res = self.run_command_with_capture(['variable=ua', 'version=%s' % v])
        self.assertIn(v, res)

        # test bad input
        with self.assertRaises(SystemExit):
            self.assertRaises(CommandError, self.cmd.run(['badoption']))

    def test_search_facets(self):
        all_facets = """cmor_table: aero,amon
product: output1
realm: aerosol,atmos
data_type: cmip5
institute: mohc
project: cmip5
time_frequency: mon
experiment: decadal2008,decadal2009,historical
variable: tauu,ua,wetso2
model: hadcm3
ensemble: r2i1p1,r7i2p1,r9i3p1
"""
        res = self.run_command_with_capture(['--all-facets'])
        self.assertEqual(res, all_facets)

        res = self.run_command_with_capture(['--facet=variable'])
        self.assertEqual(res, 'variable: tauu,ua,wetso2\n')

        res = self.run_command_with_capture(['--facet=variable', 'experiment=historical'])
        self.assertEqual(res, 'variable: wetso2\n')

        res = self.run_command_with_capture(['--facet=variable', 'facet.limit=2'])
        self.assertEqual(res, 'variable: tauu,ua...\n')

        res = self.run_command_with_capture(['--facet=variable', '--count-facet-values'])
        self.assertEqual(res, 'variable: tauu (1),ua (1),wetso2 (1)\n')

    def test_show_attributes(self):
        res = self.run_command_with_capture(['--attributes'])
        self.assertEqual(res, 'cmor_table, product, realm, data_type, institute, project, time_frequency, experiment, variable, model, ensemble\n')

    def test_solr_backwards(self):
        res = self.run_command_with_capture(['--all-facets', 'file="\/tmp/some_temp_solr_core/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/\\tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc"'])
        self.assertEqual(res, """cmor_table: amon
product: output1
realm: atmos
data_type: cmip5
institute: mohc
project: cmip5
time_frequency: mon
experiment: decadal2008
variable: tauu
model: hadcm3
ensemble: r9i3p1
""")