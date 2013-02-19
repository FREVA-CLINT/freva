'''
Created on 19.02.2013

@author: estani
'''
import unittest
import os

def loadlib(module_filepath):
    """Loads a module from a file not ending in .py"""
    import imp
    
    py_source_open_mode = "U"
    py_source_description = (".py", py_source_open_mode, imp.PY_SOURCE)
    
    module_name = os.path.basename(module_filepath)
    with open(module_filepath, py_source_open_mode) as module_file:
        return imp.load_module(
                module_name, module_file, module_filepath, py_source_description)

#load the module from a non .py file
esgf = loadlib(os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../bin/esgf')))

from evaluation_system.tests.capture_std_streams import stdout, stderr

class Test(unittest.TestCase):


    def testExistence(self):
        stdout.startCapturing()
        stdout.reset()
        esgf.main(['--help'])
        tmp = stdout.getvalue()
        self.assertTrue(len(tmp)>100)
        stdout.stopCapturing()
        
    def testEmptySearch(self):
        stdout.startCapturing()
        stdout.reset()
        esgf.main(['model=NonExistingModel', 'distrib=false'])
        tmp = stdout.getvalue()
        self.assertTrue(len(tmp)==0)
        stdout.stopCapturing()
        
    def testSearch(self):
        stdout.startCapturing()
        stdout.reset()
        esgf.main(['model=MPI-ESM-LR', 'distrib=false', 'experiment=amip4K', 'realm=landIce'])
        tmp = stdout.getvalue()
        self.assertEquals(len(tmp.splitlines()), 3)
        stdout.stopCapturing()
        
    def testMultivalueSearch(self):
        stdout.startCapturing()
        stdout.reset()
        esgf.main(['model=MPI-ESM-LR', 'distrib=false', 'experiment=amip4K', 'realm=landIce','variable=snc','variable=snm','variable=snw'])
        tmp = stdout.getvalue()
        self.assertEquals(len(tmp.splitlines()), 3)
        stdout.stopCapturing()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testAccess']
    unittest.main()