'''
Created on 18.01.2013

@author: estani
'''
import unittest

from evaluation_system.misc.utils import Struct, TemplateDict, metadict

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
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testStruct']
    unittest.main()