'''
Created on 20.09.2012

@author: estani
'''
import unittest
import os
import tempfile
from evaluation_system.tests.capture_std_streams import stderr
from evaluation_system.model.file import DRSFile, BASELINE0, BASELINE1

import logging
logging.basicConfig(level=logging.DEBUG)

class Test(unittest.TestCase):
    
    def assertItemEqual(self, iter1, iter2):
        results = []
        for i in iter1: 
            results.append(i)
        count = len(iter2)
        for i in iter2: 
            if i in results: 
                results.remove(i)
                count -= 1
        if len(results) != len(iter1) and count != 0:
            print "Items are not equal: %s , %s" % (iter1, iter2)
            assert(False)
        
    def setUp(self):
        #this will be deleted afterwards... be sure is a temporary directory!!
        self.base0 = tempfile.mkdtemp('_baseline_0')
        self.base1 = tempfile.mkdtemp('_baseline_1')
        
        DRSFile.DRS_STRUCTURE[BASELINE0]['root_dir'] = self.base0
        DRSFile.DRS_STRUCTURE[BASELINE1]['root_dir'] = self.base1
        self.real_path_0 = self.base0 + '/baseline0/output1/MPI-M/MPI-ESM-LR/decadal1960/mon/land/Lmon/r1i1p1/v20111122/c3PftFrac/c3PftFrac_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc'
        self.real_path_1 = self.base1 + '/baseline1/output/MPI-M/MPI-ESM-LR/asORAoERAa/day/atmos/pr/r1i1p1/pr_day_MPI-ESM-LR_asORAoERAa_r1i1p1_19600101-19691231.nc'
        self.real_dict = {'parts': {'cmor_table': 'Lmon', 'product': 'output1', 'realm': 'land', 'version': 'v20111122', 'institute': 'MPI-M', 'file_name': 'c3PftFrac_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc', 'project': 'baseline0', 'time_frequency': 'mon', 'experiment': 'decadal1960', 'time': '196101-199012', 'variable': 'c3PftFrac', 'model': 'MPI-ESM-LR', 'ensemble': 'r1i1p1'}, 'root_dir': self.base0}
        self.real_json = '{"parts": {"cmor_table": "Lmon", "product": "output1", "realm": "land", "version": "v20111122", "institute": "MPI-M", "file_name": "c3PftFrac_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc", "project": "baseline0", "time_frequency": "mon", "experiment": "decadal1960", "time": "196101-199012", "variable": "c3PftFrac", "model": "MPI-ESM-LR", "ensemble": "r1i1p1"}, "root_dir": "' + self.base0 + '"}'
        self.baslinefile = DRSFile(self.real_dict)

        
    def tearDown(self):
        import shutil
        #leave this hard coded.. this involves removing directories so we should be sure they are our
        for directory in [self.base0, self.base1]:
            if os.path.isdir(directory):
                shutil.rmtree(directory, True)


    def test_from_path(self):        
        print "Testing from path with path %s" % self.real_path_0
        file_dict = DRSFile.from_path(self.real_path_0)
        #check we have something
        self.assertNotEqual(file_dict, None)
        #check we have what we expect
        self.assertEqual(file_dict.dict, self.real_dict)
        
        self.failUnlessRaises(Exception, DRSFile.from_path, '/TEST' + self.real_path_0)

    def test_from_dict(self):        
        print "Testing from dict with dict %s" % self.real_dict
        file_dict = DRSFile.from_dict(self.real_dict)
        #check we have something
        self.assertNotEqual(file_dict, None)
        #check we have what we expect
        self.assertEqual(file_dict.dict, self.real_dict)

    def test_from_json(self):        
        print "Testing from json with json %s" % self.real_json
        file_dict = DRSFile.from_json(self.real_json)
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
        self.assertEqual(path, self.real_path_0)
        
    def off_test_search(self):
        result = DRSFile.search(experiment='decadal1960', variable='tas')
        #check we have something
        self.assertNotEqual(result, None)
        print "found %s files" % len([r for r in result])
        
    def test_search_wrong_constraints(self):
        stderr.startCapturing()
        stderr.reset()
        generator = DRSFile.search(non_existing_query_str='does not matter')
        #assure we got an exception
        self.failUnlessRaises(Exception, generator.next)
             
    def test_dataset(self):
        bl = DRSFile.from_json(self.real_json)
        self.assertNotEqual(bl, None)
        print "dataset (no version): %s " % bl.to_dataset()
        print "dataset (with version): %s " % bl.to_dataset(versioned=True)
        
    def test_eq(self):
        f1 = DRSFile.from_json(self.real_json)
        f2 = DRSFile.from_json(self.real_json)
        
        self.assertFalse(f1 is f2)
        self.assertTrue(f1 == f2)
        
    def test_search_baseline0(self):
        d1 = os.path.dirname(self.real_path_0)
        d2 = os.path.dirname(self.real_path_0).replace('v20111122','v20121212')
        f1a = os.path.join(d1,'v1_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc')
        f1b = os.path.join(d1,'v2_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc')
        f2a = os.path.join(d2,'v1_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc')
        
        for d in [d1,d2]:
            os.makedirs(d)

        for f in [f1a, f1b, f2a]:
            open(f, 'a').close()
            self.assertTrue(os.path.isfile(f), "can't create dummy file")
        #get all
        self.assertItemEqual(set([f1a, f1b, f2a]), set([x.to_path() for x in DRSFile.search(BASELINE0, False, model='MPI-ESM-LR')]))
        #get only the latest version (from the dataset! that means only f2a!
        #This is how datasets work d1 = f1a, f1b and then d2= f2a (it means f1a was updated and f1b *removed*)
        self.assertItemEqual(set([f2a]), set([x.to_path() for x in DRSFile.search(BASELINE0, True, model='MPI-ESM-LR')]))
            
    def test_search_baseline1(self):
        d1 = os.path.dirname(self.real_path_1)
        d2 = os.path.dirname(self.real_path_1).replace('day','mon')
        f1a = os.path.join(d1,'v1_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc')
        f1b = os.path.join(d1,'v2_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc')
        f2a = os.path.join(d2,'v1_Lmon_MPI-ESM-LR_decadal1960_r1i1p1_196101-199012.nc')
        
        for d in [d1,d2]:
            os.makedirs(d)

        for f in [f1a, f1b, f2a]:
            open(f, 'a').close()
            self.assertTrue(os.path.isfile(f), "can't create dummy file")
        #get all
        self.assertItemEqual(set([f1a, f1b, f2a]), set([x.to_path() for x in DRSFile.search(BASELINE1, False, model='MPI-ESM-LR')]))
        #There's no version stored in baseline 1, so the results should be the same
        self.assertItemEqual(set([f1a, f1b, f2a]), set([x.to_path() for x in DRSFile.search(BASELINE1, True, model='MPI-ESM-LR')]))
        #Check if we can find a specific file
        self.assertItemEqual(set([f2a]), set([x.to_path() for x in DRSFile.search(BASELINE1, True, time_frequency='mon')]))
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()