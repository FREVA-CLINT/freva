"""
Created on 15.03.2013

@author: Sebastian Illing / estani

This types represent the type of parameter a plugin expects and gives some
metadata about them.
"""
import json
from typing import Optional, Union, Type

from evaluation_system.misc.utils import find_similar_words, PrintableList, initOrder
from evaluation_system.misc import config
from evaluation_system.misc.exceptions import ValidationError
from evaluation_system.model.plugins.models import Parameter


class ParameterDictionary(dict):
    """A dictionary managing parameters for a plugin. It works just like a
    normal dictionary with some added functionality and the fact that the
    contains are stored in the same order they where defined. This order
    helps the plugin implementor to define what the user should be seeing.
    (most important parameters first, etc). Accessing the dictionary directly
    will retrieve the default value of the parameter."""

    def __init__(self, *list_of_parameters):
        """Creates a new ParameterDictionary with the given list of parameters
                objects of a sub type of :class:`ParameterType`

        :param list_of_parameters: parameters defined in order. The order will be kept,
        so it's important."""
        super().__init__()
        extra = config.get_section("scheduler_options").get("extra_options", "").strip()
        if extra.lower() == "none":
            extra = ""
        extra_scheduler_options = String(
                "extra_scheduler_options",
                default=extra,
                help=("Set additional options for the job submission to the "
                      "workload manager (, seperated). Note: batchmode and web only."
                      )
        )
        self._params = dict()
        for param in list_of_parameters:
            # check name is unique
            if param.name in self._params:
                raise ValueError(
                    "Parameters name must be unique. Got second %s key." % param.name
                )
            self._params[param.name] = param
            self[param.name] = param.default
        self._params.setdefault(extra_scheduler_options.name, extra_scheduler_options)
        self.setdefault(extra_scheduler_options.name, extra_scheduler_options)

    def __str__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join(
                ["%s<%s>: %s" % (k, self._params[k], v) for k, v in self.items()]
            ),
        )

    def get_parameter(self, param_name):
        """Return the parameter object from the given name.

        :param param_name: name of the parameter that will be returned.
        :raises: ValidationError if the parameter name doesn't match anything
        stored here."""
        if param_name not in self:
            mesg = "Unknown parameter %s" % param_name
            similar_words = find_similar_words(param_name, self.keys())
            if similar_words:
                mesg = "%s\n Did you mean this?\n\t%s" % (
                    mesg,
                    "\n\t".join(similar_words),
                )
            raise ValidationError(mesg)
        return self._params[param_name]

    def parameters(self):
        ":returns: all parameters stored in here (in order as they were defined)"
        return list(self._params.values())

    def complete(self, config_dict=None, add_missing_defaults=False):
        """Completes a given dictionary with default values if required.

        :param config_dict: the to be completed dictionary. If None, a new dictionary
        will be created.
        :param add_missing_defaults: If also parameters without any defaults should
        be completed.
        :returns: a dictionary with all missing parameters also configured."""
        if config_dict is None:
            config_dict = {}
        for key in set(self) - set(config_dict):
            if add_missing_defaults or self._params[key].default is not None:
                self._params[key].is_default = True
                config_dict[key] = self._params[key].default

        return config_dict

    def validate_errors(self, config_dict, raise_exception=False):
        """Checks if the given configuration dictionary is valied.

        :param config_dict: the dictionary to be checked.
        :param raise_exception: If an exception should be risen. In such a case only a
        message is elevated (this could be changed)
        :returns: a dictionary with missing items and those having to manay of them or
        None if no error was found."""
        missing = []
        too_many_items = []
        for key, param in self._params.items():
            if param.mandatory and (key not in config_dict or config_dict[key] is None):
                missing.append(key)
            if (
                key in config_dict
                and isinstance(config_dict[key], list)
                and len(config_dict[key]) > param.max_items
            ):
                too_many_items.append(
                    (
                        key,
                        param.max_items,
                    )
                )
        if missing or too_many_items:

            if raise_exception:
                msg = "Error found when parsing parameters. "
                if missing:
                    msg += "Missing mandatory parameters: %s" % ", ".join(missing)
                if too_many_items:
                    msg += "Too many entries for these parameters: %s" % ", ".join(
                        [
                            "%s(max:%s, found:%s)"
                            % (param, max, len(config_dict[param]))
                            for param, max in too_many_items
                        ]
                    )
                raise ValidationError(msg)
            else:
                return dict(missing=missing, too_many_items=too_many_items)

    def parseArguments(
        self, opt_arr, use_defaults=False, complete_defaults=False, check_errors=True
    ):
        """Parses an array of strings and return a dictionary with the parsed
                configuration. The strings are of the type: ``key1=val1`` or ``key2``
                multiple values can be defined by either defining the same key
                multiple times or by using the item_separator character

        :param opt_arr: List of strings containing
        ("key=value"|"key"|"key=value1,value2" iff item_separator==',')
        :param use_defaults: If the parameters defaults should be used when value
        is missing
        :param complete_defaults: Return a complete configuration containing None
        for those not provided parameters that has no defaults.
        :param check_errors: if errors in arguments should be checked."""
        config = {}
        if not isinstance(opt_arr, (list, tuple, set)):
            opt_arr = [opt_arr]
        for option in opt_arr:
            parts = option.split("=")
            if len(parts) == 1:
                key, value = parts[0], "true"
            else:
                key = parts[0]
                # just in case there were multiple '=' characters
                value = "=".join(parts[1:])

            param = self.get_parameter(key)
            if key in config:
                if not isinstance(config[key], list):
                    # we got multiple values! Instead of checking just handle
                    # accordingly and build a list
                    # if we didn't have it.
                    config[key] = [config[key]]

                if param.max_items > 1:
                    # parsing will return always a list if more than a value
                    # is expected, so don't append!
                    config[key] = config[key] + self._params[key].parse(value)
                else:
                    config[key].append(self._params[key].parse(value))
            else:
                config[key] = self._params[key].parse(value)
        if use_defaults:
            self.complete(config, add_missing_defaults=complete_defaults)

        if check_errors:
            self.validate_errors(config, raise_exception=True)

        return config

    def getHelpString(self, width=80):
        """:param width: Wrap text to this width.
        :returns: a string Displaying the help from this ParameterDictionary."""
        import textwrap

        help_str = []
        # compute maximal param length for better viewing
        max_size = max([len(k) for k in self] + [0])
        if max_size > 0:
            wrapper = textwrap.TextWrapper(
                width=width,
                initial_indent=" " * (max_size + 1),
                subsequent_indent=" " * (max_size + 1),
                replace_whitespace=False,
            )
            help_str.append("Options:")

            for key, param in self._params.items():
                param_format = "%%-%ss (default: %%s)" % (max_size)
                help_str.append(param_format % (key, param.format()))
                if param.mandatory:
                    help_str[-1] = help_str[-1] + " [mandatory]"

                # wrap it properly
                help_str.append(
                    "\n".join(wrapper.fill(line) for line in param.help.splitlines())
                )

                # help_str.append('\n') # This separates one parameter from the others

        return "\n".join(help_str)

    def synchronize(self, tool):
        """
        synchronizes the whole dictionary with the database.
        """

        for entry in self._params.values():
            entry.synchronize(tool)


class ParameterType(initOrder):
    """A General type for all parameter types in the framework"""

    _pattern = None  # laizy init.
    base_type: Optional[Union[Type[str], Type[int], Type[float], Type[bool]]] = None

    def __init__(
        self,
        name=None,
        default=None,
        mandatory=False,
        max_items=1,
        item_separator=",",
        regex=None,
        version=1,
        help="No help available.",
        print_format="%s",
        impact=Parameter.Impact.affects_values,
    ):
        """Creates a Parameter with the following information.

        :param name: name of the parameter
        :param default: the default value if none is provided
         (this value will also be validated and parsed, so it must be a *valid*
         parameter value!)
        :param mandatory: if the parameter is required
         (note that if there's a default value, the user might not be required to set
         it, and can always change it, though he/she is not allowed to *unset* it)
        :param max_items: If set to > 1 it will cause the values to be returned in a
        list (even if the user only provided 1). An error will be risen if more values
        than those are passed to the plugin
        :param item_separator: The string used to separate multiple values for this
        parameter. In some cases (at the shell, web interface, etc) the user have
        always the option to provide multiple values by re-using the same parameter
        name (e.g. @param1=a param1=b@ produces @{'param1': ['a', 'b']}@). But the
        configuration file does not allow this at this time. Therefore is better
        to setup a separator, even though the user might not use it while giving
        input. It must not be a character, it can be any string
        (make sure it's not a valid value!!)
        :param regex: A regular expression defining valid "string" values before
        parsing them to their defining classes (e.g. an Integer might define a
        regex of "[0-9]+" to prevent getting negative numbers). This will be used
        also on Javascript so don't use fancy expressions or make sure they are
        understood by both python and Javascript.
        :param help: The help string describing what this parameter is good for.
        :param print_format: A python string format that will be used when displaying
        the value of this parameter (e.g. @%.2f@ to display always 2 decimals
        for floats)
        :param impact: The impact of the parameter to the output, possible values are
        Parameter.Impact.affects_values, Parameter.Impact.affects_plots, Parameter.
        Impact.no_effects
        :param version: An internal version being 1 at default. If the parameter
        changes significantly, but appears similar to the previous version
        (default valut, name etc) than this has to be set.
        """
        self.name = name

        self.mandatory = mandatory
        if max_items < 1:
            raise ValidationError(
                "max_items must be set to a value >= 1. Current='%s'" % max_items
            )
        self.max_items = max_items
        self.item_separator = item_separator

        self.regex = regex
        self.help = help

        self.print_format = print_format

        # How important is this setting for configuration?
        self.impact = impact

        # set the version of the field
        self.version = version

        # this assures we get a valid default!
        if default is None:
            self.default = None
        else:
            self.default = self.parse(default)

        self.id = None
        self.is_default = False

    def synchronize(self, tool):
        """
        Read the id from database
        """
        if self.id is None:
            itype = self.__class__.__name__

            o = Parameter.objects.get_or_create(
                tool=tool,
                version=self.version,
                mandatory=self.mandatory,
                default=self.default,
                impact=self.impact,
                parameter_name=self.name,
                parameter_type=itype,
            )

            self.id = o[0].id

        return self.id

    def _verified(self, orig_values):

        if not isinstance(orig_values, list):
            values = [orig_values]
        else:
            values = orig_values

        if len(values) > self.max_items:
            raise ValidationError(
                "Expected %s items at most, got %s" % (self.max_items, len(values))
            )

        if (
            self.regex is not None
            and self._pattern is None
            and isinstance(values[0], str)
        ):
            import re

            self._pattern = re.compile(self.regex)

        if self._pattern:
            for val in values:
                if isinstance(val, str) and not self._pattern.search(val):
                    raise ValidationError("Invalid Value: %s" % val)

        # so it works transparent
        return orig_values

    def str(self, value):
        "Transform this value in a serializable string"
        if self.max_items > 1:
            if not isinstance(value, list):
                value = [value]
            if self.item_separator is not None:
                return self.item_separator.join(value)
            else:
                # assume is a json array:
                print(value)
                print(json.dumps(value))
                return json.dumps(value)

        else:
            return str(value)

    def parse(self, value):
        """The default parser that just passes the work to the base_type"""
        if self.max_items > 1:
            if isinstance(value, str):
                if self.item_separator is not None:
                    return [
                        self.base_type(v)
                        for v in self._verified(value.split(self.item_separator))
                    ]
                elif value[0] == "[":
                    # assume is a json array:
                    return [
                        self.base_type(v) for v in self._verified(json.loads(value))
                    ]
                else:
                    # this is a single string, but we expect multiple,
                    # so convert appropriately (in list)
                    return [self.base_type(self._verified(value))]
            else:
                # if here assume is iterable, if not see the scp
                try:
                    return [self.base_type(v) for v in self._verified(value)]
                except TypeError:
                    # it was not iterable... but we expect more than one,
                    # so return always a list
                    return [self.base_type(self._verified(value))]

        return self.base_type(self._verified(value))

    def format(self, value=None):
        """Formats the default value or the given one to a string.
                This could be overwriten to provide more control over how values are
                being displayed. This should probably be refactored to a static method.

        :param value: the value to be formated, if is set to None the default
        value will be used."""
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
        if isinstance(value, type):
            t = value
        else:
            t = type(value)
        if t in _type_mapping:
            return _type_mapping[t]()
        else:
            raise ValueError("Can't infer type for default '%s'." % value)

    def get_type(self):

        return self.__class__.__name__


class String(ParameterType):
    """A simple string parameter."""

    base_type = str


class Integer(ParameterType):
    """An integer parameter."""

    base_type = int

    def __init__(self, regex=r"^[+-]?[0-9]+$", **kwargs):
        ParameterType.__init__(self, regex=regex, **kwargs)


class Float(ParameterType):
    """A float parameter."""

    base_type = float

    def __init__(
        self,
        regex=r"^[+-]?(?:[0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)(?:[eE][+-]?[0-9]+)?$",
        **kwargs,
    ):
        ParameterType.__init__(self, regex=regex, **kwargs)


class File(String):
    """A parameter representing a file in the system."""

    def __init__(self, file_extension="nc", **kwargs):
        self.file_extension = file_extension
        ParameterType.__init__(self, **kwargs)


class Directory(String):
    """A parameter representing a directory in the system. [not used]"""

    def __init__(self, impact=Parameter.Impact.no_effects, **kwargs):
        ParameterType.__init__(self, impact=impact, **kwargs)


class InputDirectory(String):
    """A parameter representing a input directory in the system."""

    pass


class CacheDirectory(Directory):
    """A parameter representing a cache directory in the system."""

    pass


class Date(String):
    "A date parameter. [not used]" ""
    pass


class Bool(ParameterType):
    """A boolean paramter. Boolean parameters might be parsed from the
    strings as defined in :class:`Bool.parse`"""

    base_type = bool

    def parse(self, bool_str):
        """Parses a string and extract a boolean value out of it. We don't
                accept any value, the mapping is done
        in the following way (case insensitive)::

          true, t, yes, y, on, 1 => TRUE
          false, f, no, n, off, 2 => FALSE

        :param bool_str:  the string value containing a boolean value.
        :raises ValidationException: if the given string does not match any of these
        values."""
        if isinstance(bool_str, str) and bool_str:
            if bool_str.lower() in ["true", "t", "yes", "y", "on", "1"]:
                return True
            elif bool_str.lower() in ["false", "f", "no", "n", "off", "0"]:
                return False
        elif isinstance(bool_str, bool):
            # it was no bool after all...
            return bool_str
        # if here we couldn't parse it
        raise ValueError("'%s' is no recognized as a boolean default" % bool_str)


_type_mapping = {str: String, int: Integer, float: Float, bool: Bool}


"""These are the mapping of the default Python types to those of this framework.
This is mapping is used by the infer_type function to infer the type of a
given parameter default."""


class Range(String):
    """
    A range parameter. I.e passing experiment lists (1970,1975,...,2000).
    """

    def __init__(self, *args, **kwargs):
        # set max_items to a very large number...
        kwargs["max_items"] = 1e20
        self.base_type = int  # self.PrintableList
        super(Range, self).__init__(*args, **kwargs)

    def _parseColon(self, string):
        """
        Parse colon separated strings

        :param str: 'start:step:stop'
        :returns: list with integers
        """
        tmp = list(map(int, string.split(":")))
        if len(tmp) == 2:
            return list(range(tmp[0], tmp[1] + 1))
        elif len(tmp) == 3:
            return list(range(tmp[0], tmp[2] + 1, tmp[1]))
        elif len(tmp) == 1:
            return tmp
        else:
            raise ValueError("'%s' is no recognized as a range value" % str)

    def _parseComma(self, str):
        """
        Parses comma separated strings and checks each part for colon
        separated strings

        :param str: 'comma separated list
        :returns: list with integers
        """
        parts = str.split(",")
        res_list = list()
        for part in parts:
            res_list += self._parseColon(part)
        return res_list

    def parse(self, value):
        """
        Parses a "RangeString" and returns a "PrintableList"
        Value can be a comma separated string, colon separated or a combination
        Values after "-" are deleted from the resulting list

        :param value: 'start:step:stop-value' -->
        1970:5:2000-1985 or 1970:2000,1980-1990:1995
        :returns: PrintableList object
        """
        try:
            main_parts = value.split("-")
            result = self._parseComma(main_parts[0])
            del_list = PrintableList()
            for part in main_parts[1:]:
                del_list += self._parseComma(part)
            return PrintableList(sorted([x for x in result if x not in del_list]))
        except AttributeError:
            raise ValueError("'%s' is no recognized as a range value" % value)

    def str(self, value):
        return str(value)


class Unknown(String):
    """An unknown parameter for conversions"""

    def __init__(
        self, impact=Parameter.Impact.affects_values, mandatory=True, **kwargs
    ):
        ParameterType.__init__(self, impact=impact, mandatory=mandatory, **kwargs)


class SolrField(String):
    """
    A parameter using solr for finding valid values
    """

    def __init__(self, *args, **kwargs):

        self.facet = kwargs.pop("facet")
        try:
            self.group = kwargs.pop("group")
        except KeyError:
            self.group = 1
        try:
            self.multiple = kwargs.pop("multiple")
        except KeyError:
            self.multiple = False
        try:
            self.predefined_facets = kwargs.pop("predefined_facets")
        except KeyError:
            self.predefined_facets = None
        try:
            self.editable = kwargs.pop("editable")
        except KeyError:
            self.editable = True
        super(SolrField, self).__init__(*args, **kwargs)


class SelectField(String):
    def __init__(self, *args, **kwargs):

        try:
            self.options = kwargs.pop("options")
        except KeyError:
            raise KeyError(
                "You have to specifiy an options dictionary for this field type!"
            )
        super(SelectField, self).__init__(*args, **kwargs)

    def _verified(self, orig_values):

        if orig_values not in self.options.values():
            values = ",".join([v for v in self.options.values()])
            raise ValueError(
                f'Only the following values are allowed for "{self.name}": {values}'
            )
        return True

    def parse(self, value):
        if self._verified(value):
            for key, val in self.options.items():
                if value == val:
                    return key
