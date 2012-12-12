'''
Created on 18.10.2012

@author: estani
'''
import unittest
import os
from evaluation_system.tests.capture_std_streams import stdout
from evaluation_system.api.plugin import PluginAbstract, metadict
import evaluation_system.api.plugin_manager as pm
from evaluation_system.api.plugin_manager import PluginManagerException
import tempfile
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)
class DummyPlugin(PluginAbstract):
    """Stub class for implementing the abstrac one"""
    __short_description__ = None
    __version__ = (0,0,0)
    __config_metadict__ =  metadict(compact_creation=True, 
                                    number=(None, dict(type=int,help='This is just a number, not really important')),
                                    the_number=(None, dict(type=int,mandatory=True,help='This is *THE* number. Please provide it')), 
                                    something='test', other=1.4)
    _runs = []
    _template = "${number} - $something - $other"
    def runTool(self, config_dict=None):
        DummyPlugin._runs.append(config_dict)
        print "Dummy tool was run with: %s" % config_dict

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
    def setUp(self):
        pm.reloadPulgins()
        
    def testGetEnvironment(self):
        env =  analyze.getEnvironment()
        for expected in ['rows', 'columns']:
            self.assertTrue(expected in env)

    def testList(self):
        stdout.startCapturing()
        stdout.reset()
        analyze.main(['--list-tools'])
        stdout.stopCapturing()
        tool_list = stdout.getvalue()
        dummy_entry = '%s: %s' % (DummyPlugin.__name__, DummyPlugin.__short_description__)
        self.assertTrue(dummy_entry in  tool_list.splitlines()) 
        
    def testGetTool(self):
        name='DummyPlugin'
        #assure the tools can be get case insensitively
        analyze.main(['--help','--tool', name])
        analyze.main(['--help','--tool', name.lower()])
        analyze.main(['--help','--tool', name.upper()])
        
        #and that bad names (i.e. missing tools) causes an exception
        self.failUnlessRaises(PluginManagerException, analyze.main,['--help','--tool', 'Non Existing Tool'])
    
    def testDummyTool(self):
        stdout.startCapturing()
        stdout.reset()
        analyze.main("--tool dummyplugin --help".split())
        help_str = stdout.getvalue()
        self.assertEqual(help_str, 'DummyPlugin (v0.0.0): None\nOptions:\nnumber     (default: None)\n           This is just a number, not really important\n\nother      (default: 1.4)\n\nsomething  (default: test)\n\nthe_number (default: None) [mandatory]\n           This is *THE* number. Please provide it\n\n')
        stdout.reset()
        self.assertTrue(len(DummyPlugin._runs) == 0)
        analyze.main("--tool dummyplugin other=0.5 the_number=4738".split())
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs.pop()
        self.assertTrue(run['the_number']==4738)
        f = tempfile.mktemp('-testdummytool')
        self.assertFalse(os.path.isfile(f))
        analyze.main(("--tool dummyplugin --config-file %s --save-config other=0.5 the_number=4738" % f).split())
        #should have been created by now
        self.assertTrue(os.path.isfile(f))
        run2 = DummyPlugin._runs.pop()
        self.assertEqual(run, run2)

        #check if it's being read
        analyze.main(("--tool dummyplugin --config-file %s the_number=421" % f).split())
        run = DummyPlugin._runs.pop()
        self.assertEqual(run['the_number'], 421)
        self.assertEqual(run['other'], 0.5)
        
        os.unlink(f)
        
        #check if it's being read
        f2 = tempfile.mktemp('-testdummytool')
        analyze.main(("-n --tool dummyplugin --config-file %s --save-config" % f2).split())
        os.unlink(f2)
        
    def testShowConfig(self):
        old = DummyPlugin.__config_metadict__
        DummyPlugin.__config_metadict__ = metadict(compact_creation=True,
                                                   variable1=1,
                                                   variable2=(None,dict(type=int)),
                                                   variable3=(None,dict(mandatory=True)))
        analyze.main("--tool dummyplugin --show-config".split())
        DummyPlugin.__config_metadict__ = old
        
    def testPCA(self):
        tmpfile = tempfile.mkstemp("_pca-test.nc")
        outfile = tmpfile[1]
        infile = '%s/pca/test/test.nc' % tools_dir
        reference = '%s/pca/test/reference.nc' % tools_dir
        
        #assure the tools are there and you can get them case insensitively
        analyze.main(['-d','--tool', 'pca', 'input=' + infile, 
                      'eofs=1', 'normalize', 'bootstrap=false', 'variable=tas','outputdir=/tmp', 'pcafile=' + outfile])
        comp_cmd = r"(module load cdo; cdo diff %s %s | sed -n 's/^ *\([0-9]*\) of .*$/\1/p')2>/dev/null" % (reference, outfile)
        differences = call(comp_cmd)
        self.assertEqual(0, int(differences))

        #clean up output file        
        os.unlink(outfile)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    