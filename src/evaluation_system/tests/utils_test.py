'''
Created on 18.01.2013

@author: estani
'''
import unittest
from evaluation_system.misc.utils import Struct, TemplateDict

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
        res = t.substitute(dict(x='$b$b$b', y='$z', z='$a'), recursive=False)
        self.assertEquals(res, {'x': '222', 'y': '$z', 'z': '1'})
        res = t.substitute(dict(x='$b$b$b', y='$c', z='$a'), recursive=True)
        self.assertEquals(res, {'x': '222', 'y': '1', 'z': '1'})
        tmp = {}
        #the maximal amount depends on de order they get resolved, and in dictionaries this order is not
        #even given by anything in particular (e.g. alphabetic).
        #for a transitive sbstitution (a=b,b=c,c=d,...) the best case is always 1 and the worst is ceil(log_2(n))
        #We have a maximal_iterations of 15 so we can substitute *at least* 2^15=32768 variables
        max_it=5000
        for l in range(max_it):
            tmp['a_%s' % (l)] = '$a_%s' % (l+1)
        tmp['a_%s' % (max_it)] = 'end'
        print "Testing substitution with a variable chain (a_0=$a_1,a_1=$a_2,...,a_n='end') of  %s links." % len(tmp)
        res = t.substitute(tmp, recursive=True)
        self.assertTrue(all([r=='end' for r in res.values()]))
        
        #check recursions that doesn't work
        tmp['a_%s' % (max_it)] = '$a_0'
        self.failUnlessRaises(Exception,t.substitute, tmp, recursive=True)
        self.failUnlessRaises(Exception,t.substitute, dict(x='$y', y='$x'), recursive=True)
        self.failUnlessRaises(Exception,t.substitute, dict(x='$y', y='$z' , z='$x'), recursive=True)
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testStruct']
    unittest.main()