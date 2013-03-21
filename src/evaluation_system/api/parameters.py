'''
Created on 15.03.2013

@author: estani

This types represent the type of parameter a plugin expects and gives some metadata about them.
'''

from types import TypeType

class ValidationError(Exception):
    pass

class ParameterType(object):
    """A General type for all parameter types in the framework"""
    _pattern = None         #laizy init.
    
    def __init__(self, base_type, mandatory=False, max_items=1, item_separator=',', regex=None):
        self.base_type = base_type
        self.regex = regex
        self.mandatory = mandatory
        self.max_items = max_items
        self.item_separator = item_separator
        
    def _verified(self, orig_values):
        
        if not isinstance(orig_values, list):
            values = [orig_values]
        else:
            values = orig_values
            
        if len(values) > self.max_items:
            raise ValidationError("Expected %s items at most, got %s" % (self.max_items, len(values)))
            
        if self.regex is not None and self._pattern is None and isinstance(values[0], basestring):
            import re
            self._pattern = re.compile(self.regex)
        
        if self._pattern:
            for val in values:
                if isinstance(val, basestring) and not self._pattern.search(val):
                    raise ValidationError("Invalid Value: %s" % val)
        
        #so it works transparent
        return orig_values            
            
    def parse(self, value):
        """The default parser that just passes the work to the base_type"""
        if self.max_items > 1:
            if isinstance(value, basestring):
                return [self.base_type(v) for v in self._verified(value.split(self.item_separator))]
            else:
                #assume is iterable!
                try:
                    return [self.base_type(v) for v in self._verified(value)]
                except TypeError:
                    #it was not iterable... but we expect more than one, so return always a list
                    return [self._verified(self.base_type(value))]
                    
        
        return self._verified(self.base_type(value))
    
    def str(self):
        return self.__class__.__name__
    
    @staticmethod
    def infer_type(value):
        """Infer the type of a given value"""
        if isinstance(value, TypeType):
            t = value
        else:
            t = type(value)
        if t in _type_mapping:
            return _type_mapping[t]()
        else:
            raise ValueError("Can't infer type for value '%s'." % value)

class String(ParameterType):
    def __init__(self, **kwargs):
        ParameterType.__init__(self, str, **kwargs)

class Integer(ParameterType):
    def __init__(self, regex='^[0-9]+$', **kwargs):
        ParameterType.__init__(self, int, regex=regex, **kwargs)

class Long(ParameterType):
    def __init__(self, regex='^[0-9]+$', **kwargs):
        ParameterType.__init__(self, long, regex=regex, **kwargs)

class Float(ParameterType):
    def __init__(self, regex='^[0-9]+(?:\.[0-9]+)?$', **kwargs):
        ParameterType.__init__(self, float, **kwargs)

class File(ParameterType):
    def __init__(self, **kwargs):
        ParameterType.__init__(self, str, **kwargs)

class Date(ParameterType):
    def __init__(self, **kwargs):
        ParameterType.__init__(self, str, **kwargs)

class Bool(ParameterType):
    def __init__(self, **kwargs):
        ParameterType.__init__(self, bool, **kwargs)
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
"""These are the mapping of the default Python types to those of this framework.
This is mapping is used by the infer_type function to infer the type of a given parameter value."""