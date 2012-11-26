'''
Created on 18.10.2012

@author: estani
'''
import unittest
from evaluation_system.tests.capture_std_streams import stdout

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
analyze = loadlib('../../../bin/analyze')
    

class Test(unittest.TestCase):

    def testGetEnvironment(self):
        env =  analyze.getEnvironment()
        for expected in ['rows', 'columns']:
            self.assertTrue(expected in env)

    def testList(self):
        #we expect an error if called without parameters
        stdout.startCapturing()
        stdout.reset()
        analyze.main(['--list-tools'])
        stdout.stopCapturing()
        
    def testTool(self):
        stdout.startCapturing()
        stdout.reset()
        analyze.main(['--list-tools'])
        stdout.stopCapturing()
        
        p_list = stdout.getvalue()
        for plugin in p_list.strip().split('\n'):
            name = plugin.split(':')[0]
            print "Checking %s" % name
            #assure the tools are there and you can get them case insensitively
            analyze.main(['--help','--tool', name.lower()])
            analyze.main(['--help','--tool', name.upper()])
         

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    