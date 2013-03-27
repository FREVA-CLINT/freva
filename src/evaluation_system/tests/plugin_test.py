'''
Created on 03.12.2012

@author: estani
'''
import unittest
from evaluation_system.api.plugin import PluginAbstract, ConfigurationError
from evaluation_system.api.parameters import ParameterDictionary, String, Integer, Float,\
    Bool, Directory, ValidationError

from evaluation_system.tests.mocks import DummyPlugin, DummyUser


class Test(unittest.TestCase):
    
  
        
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
        dummy.__parameters__ = ParameterDictionary(String(name='a',mandatory=True))
        
        #the default behavior is to check for None values and fail if found
        self.failUnlessRaises(ValidationError, dummy.setupConfiguration)
        
        #it can be turned off
        res = dummy.setupConfiguration(check_cfg=False)
        self.assertEquals(res, {'a':None})

        #check template
        res = dummy.setupConfiguration(dict(num=1), check_cfg=False)
        self.assertEquals(1, res['num'])
        
        #check indirect resolution
        res = dummy.setupConfiguration(dict(num='${a}x', a=1), check_cfg=False)
        self.assertEquals("1x", res['num'])
        
        #check indirect resolution can also be turned off
        res = dummy.setupConfiguration(dict(num='${a}x', a=1), check_cfg=False, recursion=False)
        self.assertEquals("${a}x", res['num'])
        
        #check user special values work
        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'), check_cfg=False)
        self.assertEquals(user.getUserBaseDir(), res['num'])
        
        res = dummy.setupConfiguration(dict(num='$USER_BASE_DIR'), check_cfg=False, substitute=False)
        self.assertEquals('$USER_BASE_DIR', res['num'])
        
        user.cleanRandomHome()
        
        
    def testParseArguments(self):
        dummy = DummyPlugin()
        dummy.__parameters__ = ParameterDictionary(String(name='a'), String(name='b'))
        res = dummy.__parameters__.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a='1', b='2'))
        
        dummy.__parameters__ = ParameterDictionary(Integer(name='a', default=0),
                                                   Integer(name='b', default=0))
        res = dummy.__parameters__.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a=1, b=2))
        
        #even if the default value is different, the metadata can define the type
        dummy.__parameters__ = ParameterDictionary(Integer(name='a', default='1'),
                                                   Integer(name='b', default=2))
        res = dummy.__parameters__.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a=1, b=2))
        #more arguments than those expected
        dummy.__parameters__ = ParameterDictionary(Integer(name='a', default='1'))
        self.failUnlessRaises(ValidationError, dummy.__parameters__.parseArguments, "a=1 b=2".split())
        
        dummy.__parameters__ = ParameterDictionary(Bool(name='a'))
        for arg, parsed_val in [("a=1",True),("a=true",True),("a=TRUE",True),
                                ("a=0",False),("a=false",False),("a=False",False)]:
            res = dummy.__parameters__.parseArguments(arg.split())
            self.assertEqual(res, dict(a=parsed_val), 'Error when parsing %s, got %s' % (arg, res))
        
    def test_parseMetadict(self):
        dummy = DummyPlugin()
        for d, res_d in [(Integer(name='a',default=0), 1),
                         (Integer(name='a'), 1),
                         (Integer(name='a',default='0'), 1),
                         (String(name='a'), '1'),
                         (String(name='a', default=1), '1'),
                         (Bool(name='a'), True),
                         (Float(name='a'), float('1'))]:
            dummy.__parameters__= ParameterDictionary(d)
            res = dummy._parseConfigStrValue('a','1')
            self.assertEqual(res, res_d)
            
            
        
        ##check errors
        #Wrong type 
        dummy.__parameters__=ParameterDictionary(Integer(name='a'))
        self.failUnlessRaises(ValidationError,dummy._parseConfigStrValue,'a', 'd')
        #worng key
        self.failUnlessRaises(ValidationError,dummy._parseConfigStrValue,'b', '1')

        
    def testReadConfigParser(self):
        from ConfigParser import SafeConfigParser
        from StringIO import StringIO
        conf = SafeConfigParser()
        conf_str = "[DummyPlugin]\na=42\nb=text"
        conf.readfp(StringIO(conf_str))
        dummy = DummyPlugin()
        
        #check parsing
        for d, res_d in [([Integer(name='a')], dict(a=42)),
                         ([String(name='a')], dict(a='42')),
                         ([Integer(name='a'), String(name='b')], dict(a=42,b='text'))]:
            dummy.__parameters__= ParameterDictionary(*d)
            res = dummy.readFromConfigParser(conf)
            self.assertEqual(res, res_d)
        
        ###check errors
        #wrong type
        dummy.__parameters__= ParameterDictionary(Integer(name='b'))
        self.failUnlessRaises(ValidationError, dummy.readFromConfigParser, conf)
        #wrong regex
        dummy.__parameters__= ParameterDictionary(Integer(name='a', regex='14[0-9]*'))
        self.failUnlessRaises(ValidationError, dummy.readFromConfigParser, conf)
        
    def testSaveConfig(self):
        from StringIO import StringIO
        res_str = StringIO()
        dummy = DummyPlugin()
        dummy.__parameters__= ParameterDictionary(Integer(name='a', help=''), Integer(name='b', help=''))
        tests= [(dict(a=1), '[DummyPlugin]\na=1'),
                (dict(a='1'), '[DummyPlugin]\na=1'),
                (dict(b=2), '[DummyPlugin]\nb=2')]
        for t, res in tests:
            res_str.truncate(0)
            dummy.saveConfiguration(res_str, t)
            self.assertEqual(res_str.getvalue().strip(), res)

        dummy.__parameters__= ParameterDictionary(Integer(name='a', help='This is \na test'),
                                                  Integer(name='b', help='Also\na\ntest.'))
        
        res_str.truncate(0)
        dummy.saveConfiguration(res_str, {'a':1})
        self.assertEqual(res_str.getvalue().strip(), '[DummyPlugin]\n#: This is\n#: a test\na=1')
        res_str.truncate(0)
        dummy.saveConfiguration(res_str, {'a':1}, include_defaults=True)
        self.assertEqual(res_str.getvalue().strip(), '[DummyPlugin]\n#: This is\n#: a test\na=1\n\n#: Also\n#: a\n#: test.\n#b=None')

        dummy.__parameters__= ParameterDictionary(Integer(name='a', help="""This is a very long and complex explanation so that we could test how it is transformed into a proper configuration file that:
    a) is understandable
    b) Retains somehow the format
    c) its compact
We'll have to see how that works out..."""),
                                            String(name='b',mandatory=True, help='Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.'),
                                            String(name='c', help="""This is to check the format is preserved
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
dj1yfk"""))
        res_str.truncate(0)
        dummy.saveConfiguration(res_str, {'a':1}, include_defaults=True)
        print res_str.getvalue()
        
    def testReadConfig(self):
        from StringIO import StringIO
        res_str = StringIO()
        dummy = DummyPlugin()
        dummy.__parameters__ = ParameterDictionary(Integer(name='a'),
                                                  String(name='b', default='test'),
                                                  Float(name='other', default=1.4))
        
        for resource, expected_dict in [('[DummyPlugin]\na=1', dict(a=1,b='test',other=1.4)),
                       ('[DummyPlugin]\na=  1   \n',dict(a=1,b='test',other=1.4)),
                       ('[DummyPlugin]\na=1\nb=2', dict(a=1,b="2",other=1.4)),
                       ('[DummyPlugin]\n#a=1\nb=2\n#asd\nother=1e10', dict(a=None,b="2",other=1e10)),
                       ('[DummyPlugin]\na=-2\nb=blah blah blah', dict(a=-2,b="blah blah blah",other=1.4))]:
            res_str.truncate(0)
            res_str.write(resource)
            res_str.seek(0)
            
            conf_dict = dummy.readConfiguration(res_str)
            self.assertEqual(conf_dict, expected_dict)
    
    def testSubstitution(self):
        dummy = DummyPlugin()
        dummy.__parameters__ = ParameterDictionary(Integer(name='a'),
                                                  String(name='b', default='value:$a'),
                                                  Directory(name='c', default='$USER_OUTPUT_DIR'))
        
        
        cfg_str = dummy.getCurrentConfig({'a':72})
        self.assertTrue('value:72' in cfg_str)
        self.assertTrue(cfg_str.startswith("""a: 72
b: - (default: value:$a [value:72])
c: - (default: $USER_OUTPUT_DIR ["""))
        
        
    
    def _verifyConfingParser(self, config_parser, section, dict_opt):
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
            
    def testHelp(self):
        dummy = DummyPlugin()
        dummy.__version__ = (1,2,3)
        dummy.__short_description__ = 'A short Description.'
        dummy.__parameters__ = ParameterDictionary(
                                   Integer(name='a',default=1,help='This is the value of a'),
                                   String(name='b', help='This is not the value of b'),
                                   String(name='example', default='test',help="let's hope people write some useful help..."))
        resource="""DummyPlugin (v1.2.3): A short Description.
Options:
a       (default: 1)
        This is the value of a
b       (default: <undefined>)
        This is not the value of b
example (default: test)
        let's hope people write some useful help..."""
        self.assertEquals(dummy.getHelp().strip(), resource.strip())
        
    def testShowConfig(self):
        user = DummyUser(random_home=True)
        dummy = DummyPlugin(user=user)

        dummy.__parameters__ = ParameterDictionary(
                                   Integer(name='a', mandatory=True, help='This is the value of a'),
                                   String(name='b', default='test', help='This is not the value of b'),
                                   Float(name='other', default=1.4, ))
        self.assertEquals(dummy.getCurrentConfig(), "    a: - *MUST BE DEFINED!*\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a=2123123)), "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a=2123123)), "    a: 2123123\n    b: - (default: test)\nother: - (default: 1.4)")
        self.assertEquals(dummy.getCurrentConfig(config_dict=dict(a='/tmp$USER_PLOTS_DIR')), "    a: /tmp$USER_PLOTS_DIR [/tmp" + 
                          user.getUserPlotsDir('DummyPlugin') + "]\n    b: - (default: test)\nother: - (default: 1.4)")

        user.cleanRandomHome()

    def testUsage(self):
        dummy = DummyPlugin()
        dummy.__parameters__ = ParameterDictionary(
                                   Integer(name='a', help='This is very important'),
                                   Integer(name='b', default=2),
                                   String(name='c', help='Well this is just an x...'))
        def_config = dummy.setupConfiguration(check_cfg=False)
        from StringIO import StringIO
        resource = StringIO() 
        dummy.saveConfiguration(resource, def_config)
        res_str1 = resource.getvalue()
        resource.truncate(0)
        dummy.saveConfiguration(resource)
        res_str2 = resource.getvalue()
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
        import re
        self.assertTrue(evaluation_system.tests.mocks.__file__.startswith(dummy.getClassBaseDir()))
        #module name should be getClassBaseDir() + modulename_with_"/"_instead_of_"." + ".pyc" or ".py" 
        module_name=os.path.abspath(evaluation_system.tests.mocks.__file__)[len(dummy.getClassBaseDir())+1:].replace('/','.')
        module_name = re.sub("\.pyc?$", "", module_name)
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