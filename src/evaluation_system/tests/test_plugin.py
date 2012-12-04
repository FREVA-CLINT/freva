'''
Created on 03.12.2012

@author: estani
'''
import unittest
from evaluation_system.api.plugin import metadict, PluginAbstract, ConfigurationError

class DummyPlugin(PluginAbstract):
    """Stub class for implementing the abstrac one"""
    __short_description__ = None
    __version__ = (0,0,0)
    _config =  metadict(compact_creation=True, number=(None, dict(type=int)), something='test', other=1.4)
    _template = "${number} - $something - $other"
    def runTool(self, config_dict=None):
        PluginAbstract.runTool(self, config_dict=config_dict)
    def getHelp(self):
        PluginAbstract.getHelp(self)
    def parseArguments(self, opt_arr, default_cfg=None):
        return PluginAbstract.parseArguments(self, opt_arr, default_cfg=default_cfg)
    def setupConfiguration(self, config_dict=None, template=None, check_cfg=True):
        return PluginAbstract.setupConfiguration(self, config_dict=config_dict, template=template, check_cfg=check_cfg)
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
        dummy = DummyPlugin()
        #the default behavoir is to check for None values and fail if found
        self.failUnlessRaises(ConfigurationError, dummy.setupConfiguration, dummy._config)
        
        #it can be turned off
        res = dummy.setupConfiguration(dummy._config,check_cfg=False)
        self.assertTrue(isinstance(res,metadict))

        #check template
        res = dummy.setupConfiguration(dict(num=1),template="$num", check_cfg=False)
        self.assertTrue(isinstance(res,str))
        self.assertEquals("1", res)
        
        #check indirect resolution
        res = dummy.setupConfiguration(dict(num='${a}x', a=1),template="$num", check_cfg=False)
        self.assertEquals("1x", res)
        
    def testParseArguments(self):
        dummy = DummyPlugin()
        res = dummy.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a='1', b='2'))
        res = dummy.parseArguments("a=1 b=2".split(), default_cfg=dict(a=0,b=0))
        self.assertEqual(res, dict(a=1, b=2))
        #even if the default value is different, the metadata can define the type
        res = dummy.parseArguments("a=1 b=2".split(), default_cfg=metadict(compact_creation=True, a=('1', dict(type=int)),b=2))
        self.assertEqual(res, dict(a=1, b=2))
        #more arguments than those expected
        self.failUnlessRaises(ConfigurationError, dummy.parseArguments, "a=1 b=2".split(), default_cfg=dict(a=0))
        #argument with undefined type
        self.failUnlessRaises(ConfigurationError, dummy.parseArguments, "a=1 b=2".split(), default_cfg=dict(a=None, b=1))
        
    def test_parseMetadict(self):
        dummy = DummyPlugin()
        res = dummy._parseConfigStrValue('a', '1', ref_dictionary=dict(a=0))
        self.assertTrue(isinstance(res, int))
        self.assertEquals(res, 1)
        res = dummy._parseConfigStrValue('a', '1', ref_dictionary=metadict(compact_creation=True, a=('0',dict(type=int))))
        self.assertEquals(res, 1)
        res = dummy._parseConfigStrValue('a', '1', ref_dictionary=dict(a='0'))
        self.assertEquals(res, '1')
        res = dummy._parseConfigStrValue('a', '1', ref_dictionary=metadict(compact_creation=True, a=('0',dict(type=bool))))
        self.assertEquals(res, True)
        res = dummy._parseConfigStrValue('a', '1', ref_dictionary=metadict(compact_creation=True, a=('0',dict(type=float))))
        self.assertTrue(abs(res-1.0)<0.00000001)
        
        ##check errors
        #None type
        self.failUnlessRaises(ConfigurationError,dummy._parseConfigStrValue,'a', '1', ref_dictionary=dict(a=None))
        #missing key
        self.failUnlessRaises(ConfigurationError,dummy._parseConfigStrValue,'a', '1', ref_dictionary=dict(b=1))
        
    def testConfigParser(self):
        from ConfigParser import SafeConfigParser
        from io import StringIO
        conf = SafeConfigParser()
        section = 'DummyPlugin'
        conf_str = "[DummyPlugin]\na=42\n"
        conf.readfp(StringIO(conf_str))
        dummy = DummyPlugin()
        
        #check parsing
        res = dummy.readFromConfigParser(conf, default_metadict=dict(a=1))
        self.assertEqual(res, dict(a=42))
        res = dummy.readFromConfigParser(conf, default_metadict=metadict(compact_creation=True, a=(1,dict(type=str))))
        self.assertEqual(res, dict(a='42'))
        res = dummy.readFromConfigParser(conf, default_metadict=dict(a='1'))
        self.assertEqual(res, dict(a='42'))
        
        ###check errors
        #None type
        self.failUnlessRaises(ConfigurationError, dummy.readFromConfigParser, conf, default_metadict=dict(a=None))
        #missing key in reference
        self.failUnlessRaises(ConfigurationError, dummy.readFromConfigParser, conf, default_metadict=dict(b=1))
        
                
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()