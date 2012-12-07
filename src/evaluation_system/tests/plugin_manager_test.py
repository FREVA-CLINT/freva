'''
Created on 23.11.2012

@author: estani
'''
import unittest
import evaluation_system.api.plugin_manager as pm
from evaluation_system.api.plugin import PluginAbstract, metadict

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
    

    def testModules(self):
        pmod = pm.getPulginModules()
        self.assertTrue(pmod is not None)
        self.assertTrue(len(pmod)>0)

    def testPlugins(self):
        #All but the dummy plugin as it should have been created after the module got imported.
        plugins = pm.getPlugins()
        old_plug_count = len(plugins)
        
        for key, p in plugins.items():
            for key in ['plugin_class', 'version', 'name', 'description']:
                self.assertTrue(key in p)
            #Assure the class is derived 
            self.assertTrue(PluginAbstract in p['plugin_class'].__bases__)
        
        #now force reload
        pm.reloadPulgins()
        self.assertEqual(len(pm.getPlugins()), old_plug_count + 1)
        self.assertTrue('dummyplugin' in pm.getPlugins())
        dummy = pm.getPlugin('dummyplugin')
        self.assertEqual(dummy['description'], DummyPlugin.__short_description__)
        self.assertEqual(dummy['version'], DummyPlugin.__version__)
        self.assertEqual(dummy['plugin_class'], DummyPlugin)
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()