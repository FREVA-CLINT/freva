'''
Created on 18.10.2012

@author: estani
'''
import unittest
import find_files

class Test(unittest.TestCase):


    def testName(self):
        #we expect an error if called without parameters
        self.failUnlessRaises(find_files.CLIError, find_files.main, [''])
        
    def testSimpleSearch(self):
        find_files.main(['model=MPI-ESM-LR', 'variable=tas', 'experiment=decadal2000', 
                         'time_frequency=mon']);


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()