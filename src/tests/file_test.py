'''
Created on 20.09.2012

@author: estani
'''
import unittest
from model.file import BaselineFile

class Test(unittest.TestCase):


    def setUp(self):
        self.real_path = '/gpfs_750/projects/CMIP5/data/cmip5/output1/MPI-M/MPI-ESM-LR/decadal1960/mon/land/Lmon/r1i1p1/v20111122/c3PftFrac/c3PftFrac_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc'
        self.real_path_v2 = '/gpfs_750/projects/CMIP5/data/cmip5/output1/MPI-M/MPI-ESM-LR/decadal1960/mon/land/Lmon/r1i1p1/v20120101/c3PftFrac/c3PftFrac_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc'
        self.real_dict = {'parts': {'cmor_table': 'Lmon', 'product': 'output1', 'realm': 'land', 'version': 'v20111122', 'institute': 'MPI-M', 'file_name': 'c3PftFrac_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc', 'project': 'cmip5', 'time_frequency': 'mon', 'experiment': 'decadal1960', 'time': '196101-199012', 'variable': 'c3PftFrac', 'model': 'MPI-ESM-LR', 'ensemble': 'r1i1p1'}, 'root_dir': '/gpfs_750/projects/CMIP5/data/'}
        self.real_json = '{"parts": {"cmor_table": "Lmon", "product": "output1", "realm": "land", "version": "v20111122", "institute": "MPI-M", "file_name": "c3PftFrac_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc", "project": "cmip5", "time_frequency": "mon", "experiment": "decadal1960", "time": "196101-199012", "variable": "c3PftFrac", "model": "MPI-ESM-LR", "ensemble": "r1i1p1"}, "root_dir": "/gpfs_750/projects/CMIP5/data/"}'
        self.baslinefile = BaselineFile(self.real_dict)
        
    def tearDown(self):
        pass


    def test_from_path(self):        
        print "Testing from path with path %s" % self.real_path
        file_dict = BaselineFile.from_path(self.real_path)
        #check we have something
        self.assertNotEqual(file_dict, None)
        #check we have what we expect
        self.assertEqual(file_dict.dict, self.real_dict)

    def test_from_dict(self):        
        print "Testing from dict with dict %s" % self.real_dict
        file_dict = BaselineFile.from_dict(self.real_dict)
        #check we have something
        self.assertNotEqual(file_dict, None)
        #check we have what we expect
        self.assertEqual(file_dict.dict, self.real_dict)

    def test_from_json(self):        
        print "Testing from json with json %s" % self.real_json
        file_dict = BaselineFile.from_json(self.real_json)
        #check we have something
        self.assertNotEqual(file_dict, None)
        #check we have what we expect
        self.assertEqual(file_dict.dict, self.real_dict)

    def test_to_path(self):
        print self.baslinefile
        path = self.baslinefile.to_path();
        #check we have something
        self.assertNotEqual(path, None)
        #check we have what we expect
        self.assertEqual(path, self.real_path)
        
    def off_test_search(self):
        result = BaselineFile.search(experiment='decadal1960', variable='tas')
        #check we have something
        self.assertNotEqual(result, None)
        print "found %s files" % len(result)
        
    def test_dataset(self):
        bl = BaselineFile.from_json(self.real_json)
        self.assertNotEqual(bl, None)
        print "dataset (no version): %s " % bl.to_dataset()
        print "dataset (with version): %s " % bl.to_dataset(versioned=True)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()