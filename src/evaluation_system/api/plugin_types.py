'''
Created on 15.03.2013

@author: estani

This types represent the type of parameter a plugin expects and gives some metadata about them.
'''

from types import TypeType

class ParameterType(object):
    """A General type for all parameter types in the framework"""
    def __init__(self, base_type):
        self.base_type = base_type
    
    def parse(self, value):
        return self.base_type(value)
    def str(self):
        return self.__class__.__name__
    @staticmethod
    def infer_type(value):
        if isinstance(value, TypeType):
            t = value
        else:
            t = type(value)
        if t in _type_mapping:
            return _type_mapping[t]()
        else:
            raise ValueError("Can't infer type for '%s'." % value)

class String(ParameterType):
    def __init__(self):
        ParameterType.__init__(self, str)

class Integer(ParameterType):
    def __init__(self):
        ParameterType.__init__(self, int)

class Long(ParameterType):
    def __init__(self):
        ParameterType.__init__(self, long)

class Float(ParameterType):
    def __init__(self):
        ParameterType.__init__(self, float)

class File(ParameterType):
    def __init__(self):
        ParameterType.__init__(self, str)

class Date(ParameterType):
    def __init__(self):
        ParameterType.__init__(self, str)

class Bool(ParameterType):
    def __init__(self):
        ParameterType.__init__(self, bool)
    def parse(self, bool_str):
        if isinstance(bool_str, basestring) and bool_str: 
            if bool_str.lower() in ['true', 't', 'yes' , 'y', 'on', '1']: return True
            elif bool_str.lower() in ['false', 'f', 'no', 'n', 'off', '0']: return False
        
        #if here we couldn't parse it
        raise ValueError("'%s' is no recognized as a boolean value" % bool_str)

_type_mapping = {
                str : String,
                int : Integer,
                float : Float,
                long : Long,
                bool: Bool
                }