"""
Created on 25.05.2016

@author: Sebastian Illing
"""
import unittest
from evaluation_system.model.repository import getVersion


class Test(unittest.TestCase):
        
    def test_get_version(self):
        # self version test
        version = getVersion('.')
        self.assertEqual(len(version), 2)

        not_versioned = getVersion('/tmp')
        self.assertEqual(not_versioned, ('unknown', 'unknown'))