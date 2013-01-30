'''
Created on 03.12.2012

@author: estani
'''
import unittest
from evaluation_system.api.plugin import metadict, PluginAbstract, ConfigurationError
from evaluation_system.tests.mocks import DummyPlugin, DummyUser

class Test(unittest.TestCase):
    def testMetadictCreation(self):
        m1 = metadict(dict(a=1,b=2,c=[1,2,3]))
        m2 = metadict(a=1,b=2,c=[1,2,3])
        self.assertTrue(m1 == m2)
        
        m3 = metadict(a=1,b=2,c=[1,2,3])
        m3.setMetadata('a',test=1)
        #metadata is just a parallel storage and should not affect the data.
        self.assertTrue(m1 == m3)
        
        #the  'compact_creation' is a special key!
        m4 = metadict(compact_creation=False, a=1,b=2,c=[1,2,3])
        self.assertTrue(m1 == m4)
        self.assertFalse('compact_creation' in m4)
        #but after creation you should be able to use it
        m4['compact_creation'] = True
        self.assertFalse(m1 == m4)
        self.assertTrue('compact_creation' in m4)
        
        #setting compact creation to True should only affect tuples! Not lists.
        m5 = metadict(compact_creation=True, a=1,b=2,c=[1,2,3])
        self.assertTrue(m1 == m5)
        #Should fail if compact_creation is set and values are bad formed (i.e. iff tuple then (value, dict)
        self.failUnlessRaises(AttributeError, metadict, compact_creation=True, a=(1, 2),b=2,c=[1,2,3])
        self.failUnlessRaises(AttributeError, metadict, compact_creation=True, a=(1, [2, 3]),b=2,c=[1,2,3])
        
        #Compact creation should produce the same outcome as the normal one
        m6 = metadict(compact_creation=True, a=(1, dict(test=1)),b=2, c=[1,2,3])
        self.assertTrue(m1 == m6)
        self.assertTrue(m3.getMetadata('a') == m6.getMetadata('a'))

    def testMetadictCopy(self):
        m = metadict(dict(a=1,b=2,c=[1,2,3]))
        n = m.copy()
        n['c'][0] = 0
        #check we have a deepcopy of the items
        self.assertTrue(n['c'][0] != m['c'][0])
        
    def testIncompleteAbstract(self):
        #this is an incomplete class not implementing all required fields
        class Incomplete(PluginAbstract):
            pass
        self.failUnlessRaises(TypeError, Incomplete)
        
    def testCompleteAbstract(self):
        """Tests the creation of a complete implementation of the Plugin Abstract class"""
        #even though it's just a stub, it should be complete.
        DummyPlugin()
        
    def testSetupConfiguration(self):
        user = DummyUser(random_home=True)
        dummy = DummyPlugin(user=user)
        dummy.__config_metadict__ = metadict(compact_creation=True, a=(None, dict(mandatory=True)))
        #the default behavior is to check for None values and fail if found
        self.failUnlessRaises(ConfigurationError, dummy.setupConfiguration)
        
        #it can be turned off
        res = dummy.setupConfiguration(check_cfg=False)
        self.assertTrue(isinstance(res,metadict))

        #check template
        res = dummy.setupConfiguration(dict(num=1),template="$num", check_cfg=False)
        self.assertTrue(isinstance(res,str))
        self.assertEquals("1", res)
        
        #check indirect resolution
        res = dummy.setupConfiguration(dict(num='${a}x', a=1),template="$num", check_cfg=False)
        self.assertEquals("1x", res)
        
        #check indirect resolution can also be turned off
        res = dummy.setupConfiguration(dict(num='${a}x', a=1),template="$num", check_cfg=False, recursion=False)
        self.assertEquals("${a}x", res)
        
        #check user special values work
        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'),template="$num", check_cfg=False)
        self.assertEquals(user.getUserBaseDir(), res)
        
        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'),template="$num", check_cfg=False, substitute=False)
        self.assertEquals('$USER_BASE_DIR', res)
        
        user.cleanRandomHome()
        
        
    def testParseArguments(self):
        dummy = DummyPlugin()
        dummy.__config_metadict__ = dict(a='', b='')
        res = dummy.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a='1', b='2'))
        
        dummy.__config_metadict__ = dict(a=0,b=0)
        res = dummy.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a=1, b=2))
        
        #even if the default value is different, the metadata can define the type
        dummy.__config_metadict__ = metadict(compact_creation=True, a=('1', dict(type=int)),b=2)
        res = dummy.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a=1, b=2))
        #more arguments than those expected
        dummy.__config_metadict__ = dict(a=0)
        self.failUnlessRaises(ConfigurationError, dummy.parseArguments, "a=1 b=2".split())
        #argument with undefined type
        dummy.__config_metadict__ = dict(a=None, b=1)
        self.failUnlessRaises(ConfigurationError, dummy.parseArguments, "a=1 b=2".split())
        
        dummy.__config_metadict__ = metadict(compact_creation=True,a=(None, dict(type=bool)))
        for arg, parsed_val in [("a=1",True),("a=true",True),("a=TRUE",True),
                                ("a=0",False),("a=false",False),("a=False",False)]:
            res = dummy.parseArguments(arg.split())
            self.assertEqual(res, dict(a=parsed_val), 'Error when parsing %s, got %s' % (arg, res))
        
    def test_parseMetadict(self):
        dummy = DummyPlugin()
        for d, res_d in [(dict(a=0), 1),
                         (metadict(a=0), 1),
                         (metadict(compact_creation=True, a=(None,dict(type=int))), 1),
                         (metadict(compact_creation=True, a=('0',dict(type=int))), 1),
                         (metadict(compact_creation=True, a=2), 1),
                         (dict(a='1'), '1'),
                         (metadict(compact_creation=True, a='2'), '1'),
                         (metadict(compact_creation=True, a=(None,dict(type=str))), '1'),
                         (metadict(compact_creation=True, a=(1,dict(type=str))), '1'),
                         (metadict(compact_creation=True, a=(None,dict(type=bool))), True),
                         (metadict(compact_creation=True, a=(None,dict(type=float))), float('1')),]:
            dummy.__config_metadict__= d
            res = dummy._parseConfigStrValue('a','1')
            self.assertEqual(res, res_d)
            
        
        ##check errors
        #None type
        dummy.__config_metadict__=dict(a=None)
        self.failUnlessRaises(ConfigurationError,dummy._parseConfigStrValue,'a', '1')
        #missing key
        dummy.__config_metadict__=dict(b=1)
        self.failUnlessRaises(ConfigurationError,dummy._parseConfigStrValue,'a', '1')

        
    def testReadConfigParser(self):
        from ConfigParser import SafeConfigParser
        from StringIO import StringIO
        conf = SafeConfigParser()
        conf_str = "[DummyPlugin]\na=42\nb=text"
        conf.readfp(StringIO(conf_str))
        dummy = DummyPlugin()
        
        #check parsing
        for d, res_d in [(dict(a=1), dict(a=42)),
                         (metadict(a=1), dict(a=42)),
                         (metadict(compact_creation=True, a=(1,dict(type=str))), dict(a='42')),
                         (dict(a='1'), dict(a='42')),
                         (dict(a=1,b='1'), dict(a=42,b='text'))]:
            dummy.__config_metadict__= d
            res = dummy.readFromConfigParser(conf)
            self.assertEqual(res, res_d)
        
        ###check errors
        #None type
        dummy.__config_metadict__ = dict(a=None)
        self.failUnlessRaises(ConfigurationError, dummy.readFromConfigParser, conf)
        #wrong type
        dummy.__config_metadict__ = dict(b=1)
        self.failUnlessRaises(ConfigurationError, dummy.readFromConfigParser, conf)
        
    def testSaveConfig(self):
        from StringIO import StringIO
        res_str = StringIO()
        dummy = DummyPlugin()
        
        tests= [(dict(a=1), '[DummyPlugin]\na=1'),
                (dict(a='1'), '[DummyPlugin]\na=1'),
                (metadict(b=2), '[DummyPlugin]\nb=2'),
                (metadict(compact_creation=True,
                          b=(2,dict(help='Example')),
                          a=('1',dict(help='Example 2'))), '[DummyPlugin]\n#: Example 2\na=1\n\n#: Example\nb=2'),
                (metadict(compact_creation=True,
                          b=(None,dict(mandatory=True, help='Example')),
                          a=(None,dict(help='Example 2'))), '[DummyPlugin]\n#: Example 2\n#a=\n\n#: [mandatory] Example\nb=<THIS MUST BE DEFINED!>')]
        for t, res in tests:
            res_str.truncate(0)
            dummy.saveConfiguration(res_str, t)
            self.assertEqual(res_str.getvalue().strip(), res)
        
        res_str.truncate(0)
        dummy.saveConfiguration(res_str, metadict(compact_creation=True, a=(1, dict(help="""This is a very long and complex explanation so that we could test how it is transformed into a proper configuration file that:
    a) is understandable
    b) Retains somehow the format
    c) its compact
We'll have to see how that works out...""")),
                                            b=(None, dict(mandatory=True, help='Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.')),
                                            c=(None, dict(help="""This is to check the format is preserved
                 \..,.-
                 .\   |         __
                 .|    .-     /  .;
           _      _|      \__/..     \ 
          \ ...\|   X Hamburg        :_
           |                           \ 
          /                            /
         -.                           |
          \  X Rheine      Berlin X    \ 
       __/                              |
      |                                 /
      |                                 \ 
     /                                   |
     \     X Cologne        Dresden  X . ,
      \                            ._-. .
     /                        __.-/
     |         X Frankfurt    \ 
      \                        \ 
       \                        \ 
        ...,.                    \ 
            /                     \.
           /                       ,.
          /                      ./
         |         Munich X     |
         \,......,__  __,  __.-. .
                    \/   -/     ..
-dj1yfk"""))))
        print res_str.getvalue()
        
    def testReadConfig(self):
        from StringIO import StringIO
        res_str = StringIO()
        dummy = DummyPlugin()
        dummy.__config_metadict__ = metadict(compact_creation=True, a=(None, dict(type=int)), b='test', other=1.4)
        
        for t, res in [(dict(a=1,b='test',other=1.4), '[DummyPlugin]\na=1'),
                       (dict(a=1,b='test',other=1.4), '[DummyPlugin]\na=  1   \n'),
                (dict(a=1,b="2",other=1.4), '[DummyPlugin]\na=1\nb=2')]:
            res_str.write(res)
            res_str.seek(0)
            
            conf_dict = dummy.readConfiguration(res_str)
            self.assertEqual(conf_dict, t)
            
    def _verifyComfingParser(self, config_parser, section, dict_opt):
        #clean up by dumping to string and reloading
        from StringIO import StringIO
        res_str = StringIO()
        config_parser.write(res_str)
        from ConfigParser import SafeConfigParser
        conf = SafeConfigParser()
        res_str.seek(0)
        conf.readfp(res_str)
        
        #first compare options in section
        self.assertEqual(set(conf.options(section)), set(dict_opt))
        #now all values
        for key in conf.options(section):
            self.assertEqual(conf.get(section, key).strip("'"), '%s' %(dict_opt[key]))
        
    def _testWriteConfigParser(self):
        from StringIO import StringIO
        res_str = StringIO()
        dummy = DummyPlugin()
        section = 'DummyPlugin'
        for d in [dict(a=1), metadict(b=1),dict(a=1,b="text"),
                  metadict(compact_creation=True,a=(1,dict(help='Value a'))),
                  metadict(compact_creation=True,a=(1,dict(help='Value a')), 
                        b=(2,dict(help='Value b')),
                        c=(3,dict(help='Value c')))]:
            res = dummy.writeToConfigParser(d)
            res_str.truncate(0)
            res.write(res_str)
            print '%s\n%s' % (d, res_str.getvalue())
            self._verifyComfingParser(res, section, d)
    
    def testHelp(self):
        dummy = DummyPlugin()
        dummy.__version__ = (1,2,3)
        dummy.__short_description__ = 'A short Description.'
        dummy.__config_metadict__ = metadict(compact_creation=True,
                                             a=(1,dict(help='This is the value of a')),
                                             b=(None, dict(help='This is not the value of b')),
                                             example=('test',dict(help="let's hope people write some useful help...")))
        res="""DummyPlugin (v1.2.3): A short Description.
Options:
a       (default: 1)
        This is the value of a

b       (default: None)
        This is not the value of b

example (default: test)
        let's hope people write some useful help..."""
        self.assertEquals(dummy.getHelp().strip(), res.strip())
        
    def testShowConfig(self):
        user = DummyUser(random_home=True)
        dummy = DummyPlugin(user=user)
        dummy.__config_metadict__ =  metadict(compact_creation=True, a=(None, dict(mandatory=True,type=int)), b='test', other=1.4)
        self.assertEquals(dummy.getCurrentConfig(), "    a: - *MUST BE DEFINED!*\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a=2123123)), "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a=2123123)), "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a='/tmp$USER_PLOTS_DIR')), "    a: /tmp$USER_PLOTS_DIR [/tmp" + 
                          user.getUserPlotsDir('DummyPlugin') + "]\n    b: - (default: test)\nother: - (default: 1.4)")

        user.cleanRandomHome()
    def testUsage(self):
        dummy = DummyPlugin()
        dummy.__config_metadict__ = metadict(compact_creation=True,
                                             a=(None,dict(type=int,help='This is very important')),
                                             b=2,
                                             c=('x',dict(help='Well this is just an x...')))
        def_config = dummy.setupConfiguration(check_cfg=False)
        def_template = dummy.setupConfiguration(template='a=$a\nb=$b\nc=$c', check_cfg=False)
        from StringIO import StringIO
        res = StringIO() 
        dummy.saveConfiguration(res, def_config)
        res_str1 = res.getvalue()
        res.truncate(0)
        dummy.saveConfiguration(res)
        res_str2 = res.getvalue()
        print def_config
        print def_template
        print res_str1
        self.assertEquals(res_str1, res_str2)
        
    def testRun(self):
        dummy = DummyPlugin()
        #no confg
        dummy.runTool()
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs[0]
        self.assertTrue(run is None)
        DummyPlugin._runs = []
        
        #direct config
        dummy.runTool(config_dict=dict(the_number=42))
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs[0]
        self.assertTrue('the_number' in run)
        self.assertTrue(run['the_number'] == 42)
        DummyPlugin._runs = []
        
    def testGetClassBaseDir(self):
        dummy = DummyPlugin()
        import evaluation_system.tests.mocks
        import os
        
        self.assertTrue(evaluation_system.tests.mocks.__file__.startswith(dummy.getClassBaseDir()))
        #module name should be getClassBaseDir() + modulename_with_"/"_instead_of_"." + ".pyc" 
        module_name=os.path.abspath(evaluation_system.tests.mocks.__file__)[len(dummy.getClassBaseDir())+1:].replace('/','.')[:-4]
        self.assertEquals(module_name, 'evaluation_system.tests.mocks')
        
    def testSpecialVariables(self):
        dummy = DummyPlugin()
        special_vars = dict(sv_USER_BASE_DIR = "$USER_BASE_DIR",
                            sv_USER_OUTPUT_DIR = "$USER_OUTPUT_DIR",
                            sv_USER_PLOTS_DIR = "$USER_PLOTS_DIR",
                            sv_USER_CACHE_DIR = "$USER_CACHE_DIR",
                            sv_SYSTEM_DATE = "$SYSTEM_DATE",
                            sv_SYSTEM_DATETIME = "$SYSTEM_DATETIME",
                            sv_SYSTEM_TIMESTAMP = "$SYSTEM_TIMESTAMP",
                            sv_SYSTEM_RANDOM_UUID = "$SYSTEM_RANDOM_UUID")
        
        result = dict([(k,v) for k,v in dummy.setupConfiguration(config_dict=special_vars,check_cfg=False).items() if k in special_vars])
        print '\n'.join(['%s=%s' % (k,v) for k,v in result.items()])
        import re
        self.assertTrue(re.match('[0-9]{8}$', result['sv_SYSTEM_DATE']))
        self.assertTrue(re.match('[0-9]{8}_[0-9]{6}$', result['sv_SYSTEM_DATETIME']))
        self.assertTrue(re.match('[0-9]{9,}$', result['sv_SYSTEM_TIMESTAMP']))
        self.assertTrue(re.match('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', result['sv_SYSTEM_RANDOM_UUID']))
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()