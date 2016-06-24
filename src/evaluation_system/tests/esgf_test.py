"""
Created on 30.05.2016

@author: Sebastian Illing
"""
import unittest
import os

from evaluation_system.commands.esgf import Command
from evaluation_system.tests.capture_std_streams import stdout


class Test(unittest.TestCase):
    def setUp(self):
        self.search_dict = {'variable': 'tas',
                            'project': 'CMIP5',
                            'product': 'output1',
                            'time_frequency': 'mon',
                            'experiment': 'decadal2000',
                            'model': 'MPI-ESM-LR',
                            'ensemble': 'r1i1p1',
                            }
        self.cmd = Command()

    def tearDown(self):
        pass

    def run_command_with_capture(self, args_list=[]):

        stdout.startCapturing()
        stdout.reset()
        self.cmd.run(args_list)
        stdout.stopCapturing()
        return stdout.getvalue()

    def test_show_facet(self):
        res = self.run_command_with_capture(['--show-facet=project,product'])
        self.assertIn('[product]', res)
        self.assertIn('[project]', res)

    def test_find_files(self):


        result_to_be = ['http://esgf1.dkrz.de/thredds/fileServer/cmip5/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                        'http://aims3.llnl.gov/thredds/fileServer/cmip5_css02_data/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/tas/1/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                        'http://esgf-data1.ceda.ac.uk/thredds/fileServer/esg_dataroot/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc']
        res = self.run_command_with_capture(['%s=%s' % (key, val) for key, val in self.search_dict.iteritems()])
        for f in result_to_be:
            self.assertIn(f, res)

        res = self.run_command_with_capture(
            ['--datasets'] + ['%s=%s' % (key, val) for key, val in self.search_dict.iteritems()]
        )
        self.assertIn('cmip5.output1.MPI-M.MPI-ESM-LR.decadal2000.mon.atmos.Amon.r1i1p1 - version: 20120529', res)

    def test_download_script(self):
        fn = '/tmp/download_test_script.sh'
        res = self.run_command_with_capture(
            ['%s=%s' % (key, val) for key, val in self.search_dict.iteritems()] + ['--download-script=%s' % fn]
        )
        self.assertTrue(os.path.isfile(fn))
        self.assertEqual(res, """Download script successfully saved to %s
""" % fn)
        os.remove(fn)
