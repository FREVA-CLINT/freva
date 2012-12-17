'''
Created on 18.10.2012

@author: estani
'''
import unittest
import os
import tempfile
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)
    
from evaluation_system.tests.capture_std_streams import stdout
import evaluation_system.api.plugin_manager as pm
from evaluation_system.tests.mocks import DummyPlugin
from evaluation_system.api.plugin import metadict
from evaluation_system.api.plugin_manager import PluginManagerException
from evaluation_system.model.user import User


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

def timedeltaToDays(time_delta):
        return time_delta.microseconds / (24.0 * 60 * 60 * 1000000) + \
                time_delta.seconds / (24.0 * 60 * 60) + \
                time_delta.days
                
class Test(unittest.TestCase):
    def setUp(self):
        pm.reloadPulgins()
        
    def tearDown(self):
        #just remove the calls to dummyplugin...
        print User().getUserDB()._getConnection().execute("DELETE FROM history WHERE tool = 'dummyplugin';")
        
        
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
        
    def testHistory(self):
        import re,json
        analyze.main("--tool dummyplugin the_number=13".split())
        run = DummyPlugin._runs.pop()
        analyze.main("--history --help".split())
        stdout.startCapturing()
        stdout.reset()
        analyze.main("--history".split())
        res = stdout.getvalue()
        
        #try to convert all lines rowids to number (so we are sure we get one per file
        [int(line.split(')')[0]) for line in res.splitlines()]
        stdout.reset()
        analyze.main("--history full_text".split())
        print stdout.getvalue()
        result = re.search(r'([0-9]{1,})[)] ([^ ]{1,}) v([^ ]{1,}) (.*) *\n({\n(?:[^}].*\n)*}\n)', stdout.getvalue(), flags=re.MULTILINE).groups()
        self.assertEqual(result[1], 'dummyplugin')
        self.assertEqual(result[2], '0.0.0')
        self.assertEqual(json.loads(result[4]), run)
        rowid = int(result[0])
        from datetime import datetime, timedelta
        from time import sleep
        sleep(0.1)
        now1 = datetime.now()
        for _ in range(10):
            analyze.main("--tool dummyplugin the_number=7".split())
        
        stdout.reset()
        analyze.main("--history full_text".split())
        result = re.search(r'^([0-9]*)[)] ([^ ]*) v([^ ]*) (.*) *\n({\n(?:[^}].*\n)*}\n)', stdout.getvalue(), flags=re.MULTILINE).groups()
        self.assertEquals(int(result[0]), rowid + 10)
        
        sleep(0.1)
        now2 = datetime.now()
        analyze.main("--tool dummyplugin the_number=15".split())
        
        #check since
        stdout.reset()
        since_val = timedeltaToDays(datetime.now()-now2+timedelta(seconds=0.05))
        analyze.main(("--history limit=10 since=%s" % since_val).split())
        res = stdout.getvalue()
        self.assertEqual(len(res.splitlines()), 1)
        self.assertEqual(int(res.split(')')[0]), rowid + 10 + 1)
        since_val = timedeltaToDays(datetime.now()-now1+timedelta(seconds=0.05))
        until_val = timedeltaToDays(datetime.now()-now2+timedelta(seconds=0.05))
        
        #check since and until
        stdout.reset()
        analyze.main(("--history limit=20 since=%s until=%s" % (since_val, until_val)).split())
        res = stdout.getvalue()
        self.assertEqual(len(res.splitlines()), 10)
        self.assertEqual(int(res.split(')')[0]), rowid + 10)

        #check finding over entry_ids
        stdout.reset()
        analyze.main(("--history limit=20 entry_ids=%s" % (rowid+5)).split())
        res = stdout.getvalue()
        self.assertEqual(len(res.splitlines()), 1)
        self.assertEqual(int(res.split(')')[0]), rowid + 5)
        
        self.failUnlessRaises(Exception, analyze.main, '--history non_existing_parameter=12'.split())
        DummyPlugin._runs = []

        
        
    def _testPCA(self):
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
    
    