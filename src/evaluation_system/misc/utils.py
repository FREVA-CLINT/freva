"""Provide different utilities that does not depend on any other internal package."""
from __future__ import annotations
import copy
from copy import deepcopy
from difflib import get_close_matches
import errno
import os
from re import split
import shlex
from subprocess import run, PIPE
from string import Template
from typing import Any, Dict, Iterable, List, TextIO, IO, Union


def run_cmd(cmd: str, **kwargs: Any) -> str:
    """Run a command via subprocess.run"""
    kwargs.setdefault("check", False)
    kwargs["stdout"] = kwargs["stderr"] = PIPE
    res = run(shlex.split(cmd), **kwargs)
    return res.stdout.decode()


def convert_str_to_timestamp(time_str: str, alternative: str = "0") -> str:
    """Convert a string representation of a time step to an iso timestamp

    Parameters
    ----------
    time_str: str
        Representation of the time step usually of form %Y%m%d%H%M or
        a variant such as %Y%m or %Y%m%dT%H%M
    alternative: str, default: 0
        If conversion fails the alternative/default value the time step
        get's assign to

    Returns
    -------
    str: ISO time string representation of the input time step, such as
         %Y %Y-%m-%d or %Y-%m-%dT%H%M%S
    """

    # Strip anything that's not a number from the stringi
    if not time_str:
        return alternative
    time_str = "".join(filter(str.isdigit, time_str))
    # Not valid if time repr empty or starts with a letter, such as 'fx'
    l_times = len(time_str)
    if not l_times:
        return alternative
    if l_times <= 4:
        # Suppose this is a year only
        return time_str.zfill(4)
    if l_times <= 6:
        # Suppose this is %Y%m or %Y%e
        return f"{time_str[:4]}-{time_str[4:].zfill(2)}"
    if l_times <= 8:
        # Suppose this is %Y%m%d
        return f"{time_str[:4]}-{time_str[4:6]}-{time_str[6:].zfill(2)}"
    date = f"{time_str[:4]}-{time_str[4:6]}-{time_str[6:8]}"
    time = time_str[8:]
    if len(time) <= 2:
        time = time.zfill(2)
    else:
        # Alaways drop seconds
        time = time[:2] + ":" + time[2 : min(4, len(time))].zfill(2)
    return f"{date}T{time}"


def get_solr_time_range(time: str, sep: str = "-") -> str:
    """Create a solr time range stamp for ingestion.

    Parameters
    ----------
    time: str
        string representation of the time range
    sep: str, default: -
        seperator for start and end time

    Returns
    -------
    str: solr time range string representation
    """

    start, _, end = time.partition(sep)
    start_str = convert_str_to_timestamp(start, alternative="0")
    end_str = convert_str_to_timestamp(end, alternative="9999")
    return f"[{start_str} TO {end_str}]"


def get_console_size() -> Dict[str, int]:
    """Try getting the size of the current tty."""
    console_size = run_cmd("stty size")
    rows, columns = 25, 80
    try:
        rows, columns = tuple(map(int, console_size.strip().split()))
    except ValueError:
        pass
    return dict(rows=rows, columns=columns)


class PIPE_OUT:
    """Pipe stdout/stderr into a different handlers."""

    def __enter__(self):
        return self

    def __init__(self, *handlers: Union[IO[bytes], TextIO]):

        self.handlers = handlers

    def write(self, msg, *args, **kwargs) -> None:
        for handler in self.handlers:
            handler.write(msg, *args, **kwargs)
            # name = handler.name.lower()
            # if name != "<stdout>" and name != "<stderr>":
            #    handler.flush()

    def flush(self) -> None:
        for handler in self.handlers:
            handler.flush()

    def __exit__(self, *args, **kwargs) -> None:
        return None


def supermakedirs(path, mode):
    """
    This snippet of code was taken from stackoverflow.com
    On some systems the parameter for the access rights are ignored when
    using os.makedirs.
    This routine overcomes this problem.
    """
    # this is a neccessary condition,
    # otherwise the path will be created twice
    try:
        if path[-1] == "/":
            path = path[:-1]
    except IndexError:
        pass

    if not path or os.path.exists(path):
        return []
    (head, tail) = os.path.split(path)
    res = supermakedirs(head, mode)
    # In some rare cases we run into race conditions creating directories.
    # This prevents the system from raising an error
    try:
        os.mkdir(path)
        os.chmod(path, mode)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        pass
    res += [path]
    return res


def mp_wrap_fn(args):
    """
    Wrapper for multi-processing functions with more than one argument.
    :type args: tuple
    :param args: the function name and its arguments
    """

    function_to_call = args[0]
    args = args[1:]

    return function_to_call(*args)


class Struct:
    """This class is used for converting dictionaries into classes in order
        to access them
    more comfortably using the dot syntax."""

    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __getattr__(self, name):
        return None

    def validate(self, value):
        """Check the value is one of the possibilities from those stored
                in the object.

        :param str_value: the value to check."""
        return value in self.__dict__.values()

    def toDict(self):
        """Transfrom this struct into a dictionary."""
        result = {}
        for i in self.__dict__:
            if isinstance(self.__dict__[i], Struct):
                result[i] = self.__dict__[i].toDict()
            else:
                result[i] = self.__dict__[i]
        return result

    def __repr__(self):
        def to_str(val):
            if isinstance(val, str):
                return "'" + val + "'"
            return val

        return "<%s>" % ",".join(
            [
                "%s:%s" % (att, to_str(self.__dict__[att]))
                for att in self.__dict__
                if not att.startswith("_")
            ]
        )

    def __eq__(self, other):
        if isinstance(other, Struct):
            return self.toDict().__eq__(other.toDict())

    def __hash__(self):
        return 0

    @staticmethod
    def from_dict(dictionary, recurse=False):
        """Transforms a dict into an object.

        :param dictionary: the dictionary that will be transformed.
        :param recurse: if it would be applied recursive to other internal dictionaries.
        :type recurse: bool"""
        dictionary = copy.deepcopy(dictionary)

        # we don't need to recurse if this is not a non-empty iterable sequence
        if not dictionary:
            return dictionary

        # If a list, apply to elements within
        if type(dictionary) == list:
            return list(map(lambda d: Struct.from_dict(d, recurse), dictionary))
        # not a dictionary, return unchanged
        if type(dictionary) != dict:
            return dictionary
        if recurse:
            for key in dictionary:
                dictionary[key] = Struct.from_dict(dictionary[key], recurse)

        return Struct(**dictionary)


class TemplateDict(object):
    """Help object for resolving dictionaries containing substitutable values.
    This object has a *basis* dictionary and a resolution dictionary. The only
    difference among them is that the *basis* dictionary is defined on creation
    and the resolution dictionary is provided when calling the substitution.
    For everything else they work alike and both may contain parameterless functions
    instead of simple values that will get called when resolving them.

    This object uses the :py:class:`string.Template` object for performing
    substitution so the syntax used for substitution is as defined there
    (e.g. ``${var_to_replace}$another_var_to_replace``)."""

    translation_dict = None
    """Stores the translation dictionary used every time
    :class:`TemplateDict.substitute` is call."""

    def __init__(self, **translation_dict):
        """Create a dictionary from the named arguments passed along::

            TempleDict(a='now: $b', b=lambda: datetime.now(), c=lambda: sys.env['PWD'])

        This dictionary is stored at :class:`TemplateDict.translation_dict`."""
        self.translation_dict = translation_dict

    def __wrapDict(self, var_dict={}):
        """Creates a wrapper that acts like a dictionary to the outside but
                performs some operations
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
            for key in list(var_dict.keys()) + list(templ_self.translation_dict.keys()):
                yield (key, self[key])

        return type("dict_wrapper", (object,), {"__getitem__": f, "items": i})()

    def substitute(
        self, substitute_dict: dict[str, Any], recursive: bool = True
    ) -> dict[str, Any]:
        """Substitute the values from substitute dictionary. Values in
                ``substitute_dict`` take precedence from those in
                :class:`TemplateDict.translation_dict`.

        :type recursive: bool
        :param recursive: if the substitution should be resolved recursive by
        including the given
        :type substitute_dict: dict
        :param substitute_dict: is a dictionary of the form: ``variable -> value``.

        ``value`` in ``substitute_dict`` may be any of:
             * a simple value (int, float, str, object).
             * a string containing ``$`` characters as start marks for variables
             which must exists in either ``substitute_dict``
             or :class:`TemplateDict.translate_dict`.
             * a parameterless function returning any of the previous values.

        For instance, given this setup::

            from evaluation_system.misc.utils import TemplateDict
            from time import time
            my_dict = TemplateDict(A='Something: $B',
                                   B='milliseconds ($C)',
                                   C=lambda: '%.12f' % (time() * 1000))
            to_resolve = dict(c='$A', d='The Time in $e', e=lambda: '$B')

        Example:
        --------

            my_dict.substitute(to_resolve)
            {'c': 'Something: milliseconds (1358779343538.392089843750)',
            'e': <function <lambda> at 0xb6f0d374>,
            'd': 'The Time in milliseconds (1358779343538.410888671875)'}

        As you can see functions remain as functions in the ``substitute_dict``
        but they are used for resolution.
        Though there's no guarantee in which order resolution takes place, so
        there's no guarantee that functions are called only once. For instance
        in the example above you see two different calls to :py:func:`time.time`.
        The complete resolution was:

        * For **c**: c = '$A' -> 'Something: $B' -> 'Something: milliseconds ($C)'
                       -> 'Something: milliseconds (1358779343538.392089843750)'
        * For **d**: d = 'The time in $e' -> 'The time in %s' % e()
                       -> 'The time in $B'
                       -> 'The Time in milliseconds (1358779343538.410888671875)'
        Example:
        --------
            my_dict.substitute(to_resolve, recursive=False)
            {'c': 'Something: milliseconds (1358779553514.358886718750)',
            'e': <function <lambda> at 0xb6f0d374>,
            'd': 'The Time in $e'}

        As you see the recursion on :class:`TemplateDict.translation_dict`
        is not affected, but the variables from ``substitute_dict`` are not
        used for substitution at all."""
        # we need to work in a copy if using recursion. But we do this anyways
        # to keep the code simple.
        result = substitute_dict.copy()

        if recursive:
            final_dict = self.__wrapDict(result)
        else:
            # cannot reference itself
            final_dict = self.__wrapDict()

        # accept a maximal recursion of 15 for resolving all tokens
        # 15 is a definite number larger than any thinkable recursion for this case
        max_iter = 15
        recursion = True  # just a mark to know if it's worth iterating at all
        while recursion and max_iter > 0:
            recursion = False  # assume no recursion until one possible case is found
            for var, value in result.items():

                tmpl = None
                if isinstance(value, str) and "$" in value:
                    # something that might need to get replaced!
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
            raise Exception(
                "maximum recursion depth exceeded."
                + "Check the substitution variables are not referencing in a loop.\n"
                + "last state: %s" % ["%s=%s," % (k, v) for k, v in final_dict.items()]
            )

        return result


def find_similar_words(word: str, list_of_valid_words: Iterable[str]) -> List[str]:
    """This function implements a "Did you mean? xxx" search algorith.

    It is used for helping the user find the right word.

    Parameters:
    -----------
    word:
        the word the user selected.
    list_of_valid_words:
        a list of valid words.
    Returns:
    --------
    list : a list of words that are close to the word given"""
    expand_list = {}
    for w in list_of_valid_words:
        for w_part in split(r"[ _\-:/]", w):
            if w_part not in expand_list:
                expand_list[w_part] = set([w])
            else:
                expand_list[w_part].add(w)
    result = get_close_matches(word, expand_list)
    return [w for parts in result for w in expand_list[parts]]


class metadict(dict):
    """A dictionary extension for storing metadata along with the keys.
    In all other cases, it behaves like a normal dictionary."""

    def __init__(self, *args, **kw):
        """Creates a metadict dictionary.
        If the keyword ``compact_creation`` is used and set to ``True`` the
        entries will be given like this:

            key1=(value1, dict1) or key2=value2

        Where dict1 is the dictionary attached to the key providing its
        meta-data (key2 has no meta-data, by the way)."""
        self.metainfo = {}
        compact_creation = kw.pop("compact_creation", False)
        if compact_creation:
            # separate the special "default" in the first field from the
            # dictionary in the second
            super(metadict, self).__init__()
            for key, values in kw.items():
                if isinstance(values, tuple):
                    if len(values) != 2:
                        raise AttributeError(
                            (
                                "On compact creation a tuple with only 2 values is"
                                " expected: (default, metadata)"
                            )
                        )
                    if not isinstance(values[1], dict):
                        raise AttributeError("metadata entry must be a dictionary")
                    self[key] = values[0]
                    self.metainfo[key] = values[1]
                else:
                    self[key] = values
        else:
            super(metadict, self).__init__(*args, **kw)

    def copy(self):
        """:return: a deep copy of this metadict."""
        return deepcopy(self)

    def getMetadata(self, key):
        """Meta-data value associated with this key."""
        if key in self.metainfo:
            return self.metainfo[key]
        else:
            return None

    def setMetadata(self, key, **meta_dict):
        """Store/replace the meta-data allocated for the given key.

        :raises: KeyError if key is not present."""
        if key not in self:
            raise KeyError(key)
        if key not in self.metainfo:
            self.metainfo[key] = {}
        self.metainfo[key].update(meta_dict)

    def clearMetadata(self, key):
        """Clear all meta-data allocated under the given key.

        :raises: KeyError if key is not present."""
        if key not in self:
            raise KeyError(key)
        if key in self.metainfo:
            del self.metainfo[key]

    def put(self, key, value, **meta_dict):
        """Puts a key,value pair into the dictionary and all other keywords are added
        as meta-data to this key. If key was already present, it will be
        over-written and its meta-data will be removed
        (even if no new meta-data is provided)."""
        self[key] = value
        if meta_dict:
            self.clearMetadata(key)
            self.setMetadata(key, **meta_dict)

    @staticmethod
    def hasMetadata(some_dict, key=None):
        """if the given dictionary has meta-data for the given key or, if no key was given,
         if the dictionary can hold meta-data at all.

        Returns:
        --------
         bool: bool
            if ``some_dict`` has stored meta-data for ``key`` or
            any meta-data at all if ``key==None``."""
        if key is None:
            return hasattr(some_dict, "getMetadata")
        else:
            return hasattr(some_dict, "getMetadata") and bool(
                some_dict.getMetadata(key)
            )

    @staticmethod
    def getMetaValue(some_dict, key, meta_key):
        """This method allows to work both with normal dictionaries and metadict transparently.

        :returns: the meta-data associated with the key if any or None if not found or
                  this is not a metadict at all."""
        if metadict.hasMetadata(some_dict):
            meta = some_dict.getMetadata(key)
            if meta and meta_key in meta:
                return meta[meta_key]


class PrintableList(list):
    """
    Helper class which overwrites the __str__ function of list objects
    """

    def __init__(self, *args, **kwargs):
        try:
            self.seperator = kwargs.pop("seperator")
        except KeyError:
            self.seperator = ","
        super(PrintableList, self).__init__(*args, **kwargs)

    def __str__(self):  # pragma: no cover
        """
        :returns: String with comma separated list entries
        """
        return self.seperator.join(map(str, self))

    def __unicode__(self):  # pragma: no cover
        return self.__str__()


class initOrder(object):
    """
    Objects derived by this class get a natural order in the way they are
    initialized. This works especially for several class variables.
    """

    __counter = 0

    def __init__(self):
        self.__number = initOrder.__counter
        initOrder.__counter += 1

    def initCompare(self, other):
        return self.__number - other.__number
