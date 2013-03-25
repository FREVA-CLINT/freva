#coding=utf-8
'''
Created on 15.03.2013

@author: estani
'''

import unittest
from evaluation_system.api.parameters import \
    ParameterType, ParameterDictionary, \
    String, Float, Long, Integer, Bool, File, Date, \
    ValidationError

class Test(unittest.TestCase):


    def testInferType(self):
        self.assertEquals(ParameterType.infer_type(1).__class__, Integer)
        self.assertEquals(ParameterType.infer_type(1.0).__class__, Float) 
        self.assertEquals(ParameterType.infer_type(1L).__class__, Long)  
        self.assertEquals(ParameterType.infer_type('str').__class__, String)
        self.assertEquals(ParameterType.infer_type(True).__class__, Bool)    

    def testParsing(self):
        test_cases = [(String(), 
                            [('asd', 'asd'), (None, 'None'), (1, '1'), (True, 'True')],
                            []),
                      (String(regex='^x.*$'), 
                            [('xasd', 'xasd')],
                            ['aaaa', 'the x is not in, the right place']),
                      (String(regex='x+', max_items=3), 
                            [('xasd', ['xasd']),('xas,sxd,somex', ['xas','sxd','somex'])],
                            ['missing a letter', 'ok x, also ok xx, but not ok']),
                      (Integer(),
                            [('123',123),('0', 0),('-1',-1), (True, 1)],    #Do we really want this?!
                            ['+-0', 'not a number!!', None]),
                      (Integer(max_items=2,item_separator=','),
                            [('123',[123]),('0,4', [0, 4]), ([0L,3.1516], [0, 3]), ([0.999],[0]), (123.8,[123])],
                            ['+-0', 'not a number!!', [1,2,3]]),
                      (Float(),
                            [('123',123.0),('0', 0.0),('-1.3',-1.3), ('-1e+2',-100.0), ('+2E-2', 0.02), (False, 0.0),
                              ('12.', 12.0), ('.42', 0.42)],
                            ['+-0', 'not a number!!', '123,321.2',  None]),
                      (Long(),
                            [('123',123L),('0', 0L),('-1',-1L), (True, 1L)],    #Do we really want this?!
                            ['+-0', 'not a number!!', None]),
                      (Bool(),
                            [('1',True),('0', False),('True',True), ('false', False),
                             ('no', False), ('YES', True)],    #Do we really want this?!
                            ['maybe', '', None]),
                      
                      ]
        for case_type, positive_cases, negative_cases in test_cases:
            for expected, result in positive_cases:
                parsed_value = case_type.parse(expected)
                if isinstance(parsed_value, list):
                    self.assertEquals(type(parsed_value[0]), case_type.base_type)
                else:
                    self.assertEquals(type(parsed_value), case_type.base_type)
                self.assertEquals(parsed_value, result)
            for unparseable in negative_cases:
                try:
                    self.failUnlessRaises(TypeError, case_type.parse, unparseable)
                except:
                    try:
                        self.failUnlessRaises(ValueError, case_type.parse, unparseable)
                    except:
                        self.failUnlessRaises(ValidationError, case_type.parse, unparseable)
                    
    def testParametersDictionary(self):
        p1 = String(name='param1', default='default default 1')
        p2 = String(name='param2', default='default default 2', max_items=3, item_separator=':')
        self.assertEquals(p2.parse('a:b:C'), ['a', 'b', 'C'])

        p_dict = ParameterDictionary(p1,p2)
        self.assertTrue(len(p_dict) == 2)
        self.assertTrue(p1.name in p_dict and p_dict[p1.name] == p1.default)
        self.assertTrue(p2.name in p_dict and p_dict[p2.name] == p2.default)
        self.assertEquals(len(p_dict.parameters()), 2)
        self.assertEquals(p_dict.get_parameter(p1.name), p1)
        self.assertEquals(p_dict.get_parameter(p2.name), p2)
        
        #Check parameters remain in the order we put them
        params = []
        for i in range(1000):
            params.append(String(name=str(i), default=i))
        p_dict = ParameterDictionary(*params)
        self.assertEqual(p_dict.keys(), [p.name for p in params])
        self.assertEqual(p_dict.values(), [p.default for p in params])
        self.assertEqual(p_dict.parameters(), params)
            
    def testParseArguments(self):
        
        p_dict = ParameterDictionary(String(name='a'), String(name='b'))        
        res = p_dict.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a='1', b='2'))

        p_dict = ParameterDictionary(Integer(name='a'),Integer(name='b')) 
        res = p_dict.parseArguments("a=1 b=2".split())
        self.assertEqual(res, dict(a=1, b=2))

        #more arguments than those expected
        p_dict = ParameterDictionary(Integer(name='a'))
        self.failUnlessRaises(ValidationError, p_dict.parseArguments, "a=1 b=2".split())

        p_dict = ParameterDictionary(Integer(name='int'), 
                                     Long(name='long'),
                                     Float(name='float'), 
                                     Bool(name='bool'),
                                     String(name='string'),
                                     File(name='file', default='/tmp/file1'),
                                     Date(name='date'))
        res = p_dict.parseArguments("int=1 long=1 date=1 bool=1".split())
        self.assertEqual(res, dict(int=1, date='1', bool=True, long=1L))
        
        res = p_dict.parseArguments("int=1 long=1 date=1 bool=1".split(), use_defaults=True)
        self.assertEqual(res, dict(int=1, date='1', bool=True, long=1L, file='/tmp/file1'))

        res = p_dict.parseArguments("int=1 long=1 date=1 bool=1".split(), use_defaults=True, complete_defaults=True)
        self.assertEqual(res, dict(int=1, date='1', bool=True, long=1L, file='/tmp/file1', float=None, string=None))

        for arg, parsed_val in [("bool=1",True),("bool=true",True),("bool=TRUE",True),
                               ("bool=0",False),("bool=false",False),("bool=False",False),
                               ("bool=no",False),("bool=NO",False),("bool=YES",True),
                               ("bool", True),  #Special case!
                               ("float=1.2", 1.2),("float=-1e-1",-0.1),("float=2E2",200.0),
                               ("long=0", 0L), ("long=-42", -42L), 
                               ("string=1", "1"), ("string=ä", "ä")]:
            res = p_dict.parseArguments(arg.split())
            self.assertEqual(res, {arg.split('=')[0]:parsed_val}, 'Error when parsing %s, got %s' % (arg, res))

        #multiple arguments
        p_dict = ParameterDictionary(File(name='file', default='/tmp/file1', max_items=2, item_separator=':'),
                                     Date(name='date', item_separator='/'))
        self.assertEquals(p_dict.parseArguments(["file=a:b"]), dict(file=['a','b']))
        self.failUnlessRaises(ValidationError, p_dict.parseArguments, ["file=a:b:c"])
        #this should still work since max_items defaults to 1 and in that case no splitting happens
        self.assertEquals(p_dict.parseArguments(["date=a/b"]), dict(date="a/b"))
        self.assertEquals(p_dict.parseArguments(["file=a", "file=b"]), dict(file=['a','b']))
                          
        
    def testComplete(self):
        p_dict = ParameterDictionary(Integer(name='int'), 
                                     File(name='file', default='/tmp/file1'),
                                     Date(name='date'))
        conf = dict(int=1)
        p_dict.complete(conf)
        self.assertEquals(conf, {'int': 1, 'file': '/tmp/file1'})
        p_dict.complete(conf, add_missing_defaults=True)
        self.assertEquals(conf, {'int': 1, 'date': None, 'file': '/tmp/file1'})

        self.assertEquals(p_dict.complete(), {'file': '/tmp/file1'})
        self.assertEquals(p_dict.complete(add_missing_defaults=True), {'int': None, 'date': None, 'file': '/tmp/file1'})

        #assure default value gets parsed (i.e. validated) when creating Parameter
        p = ParameterDictionary(Integer(name='a', default='0'))
        self.assertEquals(p.complete(add_missing_defaults=True), {'a':0})
        
    def testDefaults(self):
        #All these should cause no exception
        Bool(name='a', default=True)
        Bool(name='a', default="True")
        Bool(name='a', default="0")
        Float(name='a', default=1.2e-2)
        Float(name='a', default="1.2e-2")
        Integer(name='a', default='1232')
        
    def testValidateErrors(self):
        p_dict = ParameterDictionary(Integer(name='int', mandatory=True), 
                                     File(name='file', max_items=2, item_separator=':'),
                                     Float(name='float',mandatory=True, max_items=2))
        self.assertTrue(p_dict.validate_errors(dict(int=1, float=2.0)) is None)
        self.assertEquals(p_dict.validate_errors({'int':None}), 
                          {'too_many_items': [], 'missing': ['int', 'float']})

        self.assertEquals(p_dict.validate_errors({'int':[1,2,3,4,5]}), 
                          {'too_many_items': [('int',1)], 'missing': ['float']})
        self.assertEquals(p_dict.validate_errors({'int':[1,2,3,4,5]}), 
                          {'too_many_items': [('int',1)], 'missing': ['float']})
        
        
    def testHelp(self):
        p_dict = ParameterDictionary(
                     Integer(name='answer',help='just some value', default=42, print_format='%sm'),
                     Float(name='other',help='just some super float', default=71.7, print_format='%.2f'))
        print p_dict.getHelpString()
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testInferType']
    unittest.main()