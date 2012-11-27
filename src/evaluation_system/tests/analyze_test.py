'''
Created on 18.10.2012

@author: estani
'''
import unittest
import os
from evaluation_system.tests.capture_std_streams import stdout

def loadlib(module_filepath):
    """Loads a module from a file not ending in .py"""
    #Try to tell python not to write these compiled files to disk
    import sys
    sys.dont_write_bytecode = True
    
    import imp
    
    py_source_open_mode = "U"
    py_source_description = (".py", py_source_open_mode, imp.PY_SOURCE)
    
    module_name = os.path.basename(module_filepath)
    with open(module_filepath, py_source_open_mode) as module_file:
        return imp.load_module(
                module_name, module_file, module_filepath, py_source_description)

#load the module from a non .py file
analyze = loadlib('../../../bin/analyze')
tools_dir = os.path.join(__file__[:-len('src/evaluation_system/tests/analyze_test.py')-1],'tools')

def call(cmd_string):
    """Simplify the interaction with the shell.
    Parameters
    cmd_string : string
        the command to be issued in a string"""
    from subprocess import Popen, PIPE, STDOUT
    #workaround: the script test for PS1, setting it makes it beleave we are in an interactive shell
    cmd_string = 'export PS1=x; . /etc/bash.bashrc >/dev/null;' + cmd_string
    p = Popen(['/bin/bash', '-c', '%s' % (cmd_string)], stdout=PIPE, stderr=STDOUT)
    return p.communicate()[0]

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
            
    def testPCA(self):
        import tempfile
        tmpfile = tempfile.mkstemp("_pca-test.nc")
        outfile = tmpfile[1]
        infile = '%s/pca/test/test.nc' % tools_dir
        reference = '%s/pca/test/reference.nc' % tools_dir
        
        #assure the tools are there and you can get them case insensitively
        analyze.main(['--tool', 'pca', 'input=' + infile,
                      'eofs=1', 'normalize', 'variable=tas','outputdir=/tmp', 'pcafile=' + outfile])
        comp_cmd = r"(module load cdo; cdo diff %s %s | sed -n 's/^ *\([0-9]*\) of .*$/\1/p')2>/dev/null" % (reference, outfile)
        differences = call(comp_cmd)
        self.assertEqual(0, int(differences))

        #clean up output file        
        os.unlink(outfile)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    