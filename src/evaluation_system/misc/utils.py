'''
.. moduleauthor:: estani <estanislao.gonzalez@met.fu-berlin.de>

This module provides different utilities that does not depend on any other internal package.
'''
import copy

class Struct(object):
    """This class is used for converting dictionaries into classes."""

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
