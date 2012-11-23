'''
Created on 23.11.2012

@author: estani
'''
import unittest
import evaluation_system.api.plugin_manager as pm

class Test(unittest.TestCase):


    def testCreation(self):
        print pm.getPlugins()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()