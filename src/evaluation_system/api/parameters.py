'''
Created on 15.03.2013

@author: estani

This types represent the type of parameter a plugin expects and gives some metadata about them.
'''
from types import TypeType, StringType, IntType, FloatType, LongType, BooleanType

from evaluation_system.misc.py27 import OrderedDict
from evaluation_system.misc.utils import find_similar_words

class ValidationError(Exception):
    pass


class ParameterDictionary(OrderedDict):
    """A dictionary managing parameters for a plugin."""
    def  __init__(self, *list_of_parameters):
        OrderedDict.__init__(self)
        
        self._params = OrderedDict()
        for param in list_of_parameters:
            #check name is unique
            if param.name in self._params:
                raise ValueError("Parameters name must be unique. Got second %s key." % param.name)
            self._params[param.name] = param
            self[param.name] = param.default
    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(['%s<%s>: %s' % (k, self._params[k], v)for k,v in self.items()]))
    def get_parameter(self, param_name):
        if param_name not in self:
            mesg = "Unknown parameter %s" % param_name
            similar_words = find_similar_words(param_name, self.keys())
            if similar_words: mesg = "%s\n Did you mean this?\n\t%s" % (mesg, '\n\t'.join(similar_words))
            raise ValidationError(mesg)
        return self._params[param_name]
    
    def parameters(self):
        return self._params.values()
    
    def complete(self, config_dict=None, add_missing_defaults=False):
        if config_dict is None:
            config_dict = {}
        for key in set(self) - set(config_dict):
            if add_missing_defaults or self._params[key].default is not None:
                config_dict[key] = self._params[key].default
                
        return config_dict
    
    def validate_errors(self, config_dict):
        missing = []
        too_many_items = []
        for key, param in self._params.items():
            if param.mandatory and (key not in config_dict or config_dict[key] is None):
                missing.append(key)
            if key in config_dict and isinstance(config_dict[key], list) and len(config_dict[key]) > param.max_items:
                too_many_items.append((key, param.max_items,)) 
        if missing or too_many_items:
            return dict(missing=missing, too_many_items=too_many_items)
        
    def parseArguments(self, opt_arr, use_defaults=False, complete_defaults=False):
        """Parses an array of strings and return a dictionary with the parsed configuration.
The strings are of the type: ``key1=val1`` or ``key2`` multiple values can be defined by either
defining the same key multiple times or by using the item_separator character

:param opt_arr: List of strings containing ("key=value"|"key"|"key=value1,value2" iff item_separator==',')
:param use_defaults: If the parameters defaults should be used when value is missing
:param complete_defaults: Return a complete configuration containing None for those not provided 
 parameters that has no defaults.
"""
        config = {}
        
        for option in opt_arr:            
            parts = option.split('=')
            if len(parts) == 1:
                key, value = parts[0], 'true'
            else:
                key = parts[0]
                #just in case there were multiple '=' characters
                value = '='.join(parts[1:])
            

            param = self.get_parameter(key)
            if key in config:
                if not isinstance(config[key], list):
                    #we got multiple values! Instead of checking just handle accordingly and build a list
                    #if we didn't have it.
                    config[key] = [config[key]]
                    
                if param.max_items > 1:
                    #parsing will return always a list if more than a value is expected, so don't append!
                    config[key] = config[key] + self._params[key].parse(value)
                else:
                    config[key].append(self._params[key].parse(value))
            else: 
                config[key] = self._params[key].parse(value)
        if use_defaults:
            self.complete(config, add_missing_defaults=complete_defaults)
            
        return config
    
    def getHelpString(self, width=80):
        """:param width: Wrap text to this width.
:returns: a string Displaying the help from this ParameterDictionary."""
        import textwrap
        help_str = []
        #compute maximal param length for better viewing
        max_size= max([len(k) for k in self] + [0])
        if max_size > 0:
            wrapper = textwrap.TextWrapper(width=width, initial_indent=' '*(max_size+1), subsequent_indent=' '*(max_size+1), replace_whitespace=False)
            help_str.append('Options:')
        
         
            for key, param in self._params.items():
                param_format = '%%-%ss (default: %%s)' % (max_size) 
                help_str.append(param_format % (key, param.format()))
                if param.mandatory:
                    help_str[-1] = help_str[-1] + ' [mandatory]'

                #wrap it properly
                help_str.append('\n'.join(wrapper.fill(line) for line in 
                       param.help.splitlines()))
                
                #help_str.append('\n') #This separates one parameter from the others
        
        return '\n'.join(help_str)
    
class ParameterType(object):
    """A General type for all parameter types in the framework"""
    _pattern = None         #laizy init.
    base_type = None
    
    def __init__(self, name=None, default=None, 
                 mandatory=False, max_items=1, item_separator=',', regex=None,
                 help='No help available.', 
                 print_format='%s'):
        
        self.name = name
        
        self.mandatory = mandatory
        self.max_items = max_items
        self.item_separator = item_separator

        self.regex = regex
        self.help = help
        
        self.print_format = print_format 
        
        #this assures we get a valid default!
        if default is None:
            self.default = None
        else:
            self.default = self.parse(default)
        
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
            if isinstance(value, basestring) and self.item_separator is not None:
                return [self.base_type(v) for v in self._verified(value.split(self.item_separator))]
            else:
                #assume is iterable!
                try:
                    return [self.base_type(v) for v in self._verified(value)]
                except TypeError:
                    #it was not iterable... but we expect more than one, so return always a list
                    return [self.base_type(self._verified(value))]
                    
        
        return self.base_type(self._verified(value))
    
    def format(self, value=None):
        if value is None:
            if self.default is None:
                return "<undefined>"
            else:
                value = self.default
        return self.print_format % value
                
    
    def __str__(self):
        return self.__class__.__name__
    
    @staticmethod
    def infer_type(value):
        """Infer the type of a given default"""
        if isinstance(value, TypeType):
            t = value
        else:
            t = type(value)
        if t in _type_mapping:
            return _type_mapping[t]()
        else:
            raise ValueError("Can't infer type for default '%s'." % value)



class String(ParameterType):
    base_type = StringType

class Integer(ParameterType):
    base_type = IntType
    def __init__(self, regex='^[+-]?[0-9]+$', **kwargs):
        ParameterType.__init__(self, regex=regex, **kwargs)

class Long(Integer):
    base_type = LongType

class Float(ParameterType):
    base_type = FloatType
    def __init__(self, regex='^[+-]?(?:[0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)(?:[eE][+-]?[0-9]+)?$', **kwargs):
        ParameterType.__init__(self, regex=regex, **kwargs)

class File(String):
    pass

class Date(String):
    pass

class Bool(ParameterType):
    base_type = BooleanType

    def parse(self, bool_str):
        if isinstance(bool_str, basestring) and bool_str: 
            if bool_str.lower() in ['true', 't', 'yes' , 'y', 'on', '1']: return True
            elif bool_str.lower() in ['false', 'f', 'no', 'n', 'off', '0']: return False
        
        #if here we couldn't parse it
        raise ValueError("'%s' is no recognized as a boolean default" % bool_str)

_type_mapping = {
                str : String,
                int : Integer,
                float : Float,
                long : Long,
                bool: Bool
                }
"""These are the mapping of the default Python types to those of this framework.
This is mapping is used by the infer_type function to infer the type of a given parameter default."""