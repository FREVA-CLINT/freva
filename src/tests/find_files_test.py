'''
Created on 18.10.2012

@author: estani
'''
import unittest

def loadlib(module_filepath):
    """Loads a module from a file not ending in .py"""
    import os
    import imp
    
    py_source_open_mode = "U"
    py_source_description = (".py", py_source_open_mode, imp.PY_SOURCE)
    
    module_name = os.path.basename(module_filepath)
    with open(module_filepath, py_source_open_mode) as module_file:
        return imp.load_module(
                module_name, module_file, module_filepath, py_source_description)

#load the module from a non .py file
find_files = loadlib('../../bin/find_files')
    

class Test(unittest.TestCase):


    def testName(self):
        #we expect an error if called without parameters
        self.failUnlessRaises(find_files.CLIError, find_files.main, [''])
        
    def testSimpleSearch(self):
        find_files.main(['model=MPI-ESM-LR', 'variable=tas', 'experiment=decadal2000', 
                         'time_frequency=mon']);
         
        find_files.main(['--baseline', '1', 'model=MPI-ESM-LR', 'variable=tas', 'experiment=decadal2000', 
                         'time_frequency=mon']);

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    