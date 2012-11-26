'''
Created on 23.11.2012

@author: estani
'''
import unittest
import evaluation_system.api.plugin_manager as pm
from evaluation_system.api.plugin import PluginAbstract
class Test(unittest.TestCase):

    def testModules(self):
        pmod = pm.getPulginModules()
        self.assertTrue(pmod is not None)
        self.assertTrue(len(pmod)>0)

    def testPlugins(self):
        plugins = pm.getPlugins()
        print plugins
        
        for key, p in plugins.items():
            for key in ['plugin_class', 'version', 'name', 'description']:
                self.assertTrue(key in p)
            #Assure the class is derived 
            self.assertTrue(PluginAbstract in p['plugin_class'].__bases__)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()