'''
Created on 18.10.2012

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
find_files = loadlib(os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../bin/find_files')))

from evaluation_system.tests.capture_std_streams import stdout

class Test(unittest.TestCase):


    def testName(self):
        #we expect an error if called without parameters
        self.failUnlessRaises(find_files.CommandError, find_files.main, [''])
        
    def testSimpleSearch(self):
        find_files.main(['--baseline','0', 'model=MPI-ESM-LR', 'variable=tas', 'experiment=decadal2000', 
                         'time_frequency=mon']);
         
        find_files.main(['--baseline', '1', 'model=MPI-ESM-LR', 'variable=tas', 'experiment=decadal2000', 
                         'time_frequency=mon']);
    def testHelp(self):
        stdout.startCapturing()
        old_str = ""
        for data_type in ["","--baseline 0", "--baseline 1", "--cmip5", "--observations", "--reanalysis"]:
            stdout.reset()
            find_files.main(("--help %s" % data_type).split())
            help_str = stdout.getvalue()
            self.assertNotEqual(old_str, help_str)
            help_str = old_str
            
        stdout.stopCapturing()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    