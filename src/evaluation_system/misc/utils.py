'''
.. moduleauthor:: estani <estanislao.gonzalez@met.fu-berlin.de>

This module provides different utilities that does not depend on any other internal package.
'''
import copy
from difflib import get_close_matches
from string import Template
from re import split

class Struct(object):
    """This class is used for converting dictionaries into classes in order to access them
more comfortably using the dot syntax."""

    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __getattr__(self, name):
        return None
    
    def validate(self, value):
        """Check the value is one of the possibilities from those stored in the object.

:param str_value: the value to check."""
        return value in self.__dict__.values()
    
    def toDict(self):
        """Transfrom this struct into a dictionary."""
        result = {}
        for i in self.__dict__:
            if isinstance(self.__dict__[i], Struct): result[i] = self.__dict__[i].toDict()
            else: result[i] = self.__dict__[i]
        return result

    def __repr__(self):
        def to_str(val):
            if isinstance(val, basestring): return "'" + val + "'"
            return val

        return "<%s>" % ",".join([ "%s:%s" % (att, to_str(self.__dict__[att]))
                                    for att in self.__dict__ if not att.startswith('_')])
    def __eq__(self, other):
        if isinstance(other, Struct):
            return self.toDict().__eq__(other.toDict())

    @staticmethod
    def from_dict(dictionary, recurse=False):
        """Transforms a dict into an object.

:param dictionary: the dictionary that will be transformed.
:param recurse: if it would be applied recursive to other internal dictionaries.
:type recurse: bool"""
        dictionary = copy.deepcopy(dictionary)

        #we don't need to recurse if this is not a non-empty iterable sequence
        if not dictionary: return dictionary

        #If a list, apply to elements within
        if type(dictionary) == list: return map(lambda d: Struct.from_dict(d, recurse) ,dictionary)
        #not a dictionary, return unchanged
        if type(dictionary) != dict: return dictionary
        if recurse:
            for key in dictionary: dictionary[key] = Struct.from_dict(dictionary[key], recurse)

        return Struct(**dictionary)


class TemplateDict(object):
    """Help object for resolving dictionaries containing substitutable values.
This object has a *basis* dictionary and a resolution dictionary. The only difference among them is
that the *basis* dictionary is defined on creation  and the resolution dictionary is provided when 
calling the substitution. For everything else they work alike and both may contain parameterless functions
instead of simple values that will get called when resolving them.

This object uses the :py:class:`string.Template` object for performing substitution so the syntax used for
substitution is as defined there (e.g. ``${var_to_replace}$another_var_to_replace``).
"""

    translation_dict = None
    """Stores the translation dictionary used every time :class:`TemplateDict.substitute` is call."""
    
    def __init__(self, **translation_dict):
        """Create a dictionary from the named arguments passed along::

    TempleDict(a='now: $b', b=lambda: datetime.now(), c=lambda: sys.env['PWD'])

This dictionary is stored at :class:`TemplateDict.translation_dict`."""
        self.translation_dict = translation_dict

    
    def __wrapDict(self, var_dict = {}):
        """Creates a wrapper that acts like a dictionary to the outside but performs some operations
in the background when retrieving the values."""      
        templ_self = self
        
        def f(self, key):
            
            if key in var_dict:
                val = var_dict[key]
            else:
                val = templ_self.translation_dict[key]
            if callable(val): 
                return val()
            else: 
                return val

        def i(self):
            for key in var_dict.keys() + templ_self.translation_dict.keys():
                yield (key, self[key])
            
        return type('dict_wrapper', (object,), {'__getitem__':f, 'items':i})()
            
        
    def substitute(self, substitute_dict, recursive = True):
        """Substitute the values from substitute dictionary. Values in ``substitute_dict`` take precedence from
those in :class:`TemplateDict.translation_dict`.

:type recursive: bool
:param recursive: if the substitution should be resolved recursive by including the given 
:type substitute_dict: dict 
:param substitute_dict: is a dictionary of the form: ``variable -> value``. 

``value`` in ``substitute_dict`` may be any of:
     * a simple value (int, float, str, object).
     * a string containing ``$`` characters as start marks for variables which must exists in either ``substitute_dict`` or :class:`TemplateDict.translate_dict`.
     * a parameterless function returning any of the previous values.

For instance, given this setup::

    from evaluation_system.misc.utils import TemplateDict
    from time import time
    my_dict = TemplateDict(A='Something: $B', B='milliseconds ($C)', C=lambda: '%.12f' % (time() * 1000))
    to_resolve = dict(c='$A', d='The Time in $e', e=lambda: '$B')

The result of substituting ``to_resolve`` would be::

    >>> my_dict.substitute(to_resolve)
    {'c': 'Something: milliseconds (1358779343538.392089843750)', 
    'e': <function <lambda> at 0xb6f0d374>, 
    'd': 'The Time in milliseconds (1358779343538.410888671875)'}

As you can see functions remain as functions in the ``substitute_dict`` but they are used for resolution.
Though there's no guarantee in which order resolution takes place, so there's no guarantee that functions are called
only once. For instance in the example above you see two different calls to :py:func:`time.time`. 
The complete resolution was:

* For **c**: c = '$A' -> 'Something: $B' -> 'Something: milliseconds ($C)' -> 'Something: milliseconds (1358779343538.392089843750)'
* For **d**: d = 'The time in $e' -> 'The time in %s' % e() -> 'The time in $B' -> 'The Time in milliseconds (1358779343538.410888671875)'

Using ``recursive=False`` results in:
    >>> my_dict.substitute(to_resolve, recursive=False)
    {'c': 'Something: milliseconds (1358779553514.358886718750)', 
    'e': <function <lambda> at 0xb6f0d374>, 
    'd': 'The Time in $e'}

As you see the recursion on :class:`TemplateDict.translation_dict` is not affected, but the variables from
``substitute_dict`` are not used for substitution at all.
"""
        #we need to work in a copy if using recursion. But we do this anyways
        #to keep the code simple.
        result = substitute_dict.copy()
        
        if recursive:
            final_dict = self.__wrapDict(result)
        else:
            #cannot reference itself
            final_dict = self.__wrapDict()

        #accept a maximal recursion of 15 for resolving all tokens
        #15 is a definite number larger than any thinkable recursion for this case
        max_iter = 15        
        recursion = True    #just a mark to know if it's worth iterating at all
        while recursion and max_iter > 0:
            recursion = False   #assume no recursion until one possible case is found
            for var, value in result.items():
                
                tmpl = None
                if isinstance(value, basestring) and '$' in value:
                    #something that might need to get replaced!
                    tmpl = Template(value)
                elif isinstance(value, Template):
                    tmpl = value
                    
                if tmpl:
                    result[var] = tmpl.safe_substitute(final_dict)
                    recursion = True
                else:
                    result[var] = value
                    
            max_iter -= 1
        if recursive and max_iter <= 0:
            raise Exception("maximum recursion depth exceeded." + 
                            "Check the substitution variables are not referencing in a loop.\n" +
                            "last state: %s" % ['%s=%s,'%(k,v) for k,v in final_dict.items()])
        
        return result
                
def find_similar_words(word, list_of_valid_words):
    """This function implements a "Did you mean? xxx" algorith for finding similar words.
It's used for helping the user find the right word.

:param word: the word the user selected.
:param list_of_valid_words: a list of valid words.
:returns: a list of words that are close to the word given"""
    expand_list = {}
    for w in list_of_valid_words:
        for w_part in split('[ _\-:/]', w): 
            if w_part not in expand_list: expand_list[w_part] = set([w])
            else: expand_list[w_part].add(w) 
        
    result =  get_close_matches(word, expand_list)
    return [w for parts in result for w in expand_list[parts]]
    
