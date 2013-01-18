'''
Created on 18.01.2013

@author: estani
'''
import unittest
from evaluation_system.misc.utils import *

class Test(unittest.TestCase):


    def testStruct(self):
        ref_dict = {'a':1, 'b':2}
        s = Struct(**ref_dict)
        self.assertTrue('a' in s.__dict__)
        self.assertTrue(s.validate(1))
        self.assertEquals(s.a, 1)
        self.assertTrue('b' in s.__dict__)
        self.assertEquals(s.b, 2)
        self.assertTrue(s.validate(2))
        
        self.assertEquals(s.toDict(), ref_dict)
        self.assertEquals(Struct.from_dict(ref_dict), s)
        
        #recursion
        ref_dict = {'a': {'b':{'c':1}}}
        s = Struct.from_dict(ref_dict, recurse=True)
        self.assertTrue('a' in s.__dict__)
        self.assertTrue('b' in s.a.__dict__)
        self.assertTrue('c' in s.a.b.__dict__)
        self.assertTrue(s.a.b.validate(1))
        self.assertEquals(s.a.b.c, 1)

    def testTemplateDict(self):
        t = TemplateDict(a=1,b=2,c='$a')
        res = t.substitute(dict(x='$b$b$b', y='$c', z='$a'), recursive=False)
        self.assertEquals(res, {'x': '222', 'y': '$a', 'z': '1'})
        res = t.substitute(dict(x='$b$b$b', y='$c', z='$a'), recursive=True)
        self.assertEquals(res, {'x': '222', 'y': '1', 'z': '1'})
        tmp = {}
        max_it=12
        for l in range(max_it):
            tmp[chr(97+l)] = '$'+ chr(97+l+1)
        tmp[chr(97+max_it)] = 'end'
        res = t.substitute(tmp, recursive=True)
        self.failUnlessRaises(Exception,t.substitute, dict(x='$y', y='$x'), recursive=True)
        self.failUnlessRaises(Exception,t.substitute, dict(x='$y', y='$z' , z='$x'), recursive=True)
        
        print res
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testStruct']
    unittest.main()