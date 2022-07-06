"""Definitions of parameters types to configure custom ``Freva`` plugins.

Plugin parameters are defined in the plugin wrapper class. Please refer to
:class:`evaluation_system.api.plugin` for more information on how to set up a
plugin wrapper class.

"""
from __future__ import annotations
from collections import defaultdict
import json
import re
import textwrap
from typing import Any, Optional, Union, Type
import warnings

from evaluation_system.misc.utils import find_similar_words, PrintableList, initOrder
from evaluation_system.misc import config
from evaluation_system.misc.exceptions import ValidationError, deprecated_method
from evaluation_system.model.plugins.models import Parameter

ParameterBaseType = Union[str, int, float, bool, PrintableList]
"""Type definitions of all possible parameter types."""


class ParameterType(initOrder):
    """Base class for all prameter types.

     All available parameter types inherit from this class. The class creates
     a parameter object holding the following user defined information.

     Parameters
     ----------

     name: str
         Name of the parameter.
     default: ParameterBaseType, default: str
         the default value of the given parameter. **Note**: this value must be
         a *valid* parameter value!
    mandatory: bool, default: False
         boolean indicating if this parameter is required
     max_items: int, default: 1
         If set to > 1 it will cause the values to be returned in a
         list (even if the user only provided 1). Raises an error if more than
         than ``max_items`` values are parsed.
     item_separator: str, default: ,
         The string used to separate multiple values for this
         parameter. In some cases (at the shell, web interface, etc) the user have
         always the option to provide multiple values by re-using the same parameter
         name (e.g. ``param1=a param1=b`` produces ``{'param1': ['a', 'b']}``). But the
         configuration file does not allow this at this time. Therefore is better
         to setup a separator, even though the user might not use it while giving
         input. It must not be a character, it can be any string
         (make sure it's not a valid value!!)
     regex: Optional[str], default: None
         A regular expression defining valid "string" values before
         parsing them to their defining classes (e.g. an Integer might define a
         regex of "[0-9]+" to prevent getting negative numbers). This will be used
         also on Javascript so don't use fancy expressions or make sure they are
         understood by both python and Javascript.
     help: str, default: No help available
         The help string describing what this parameter is good for.
     print_format: str, default %s
         String format used to display parameter values, e.g. ``%.2f`` to
         display always 2 decimals for floats
     impact:
         The impact of the parameter to the output, possible values are
         Parameter.Impact.affects_values, Parameter.Impact.affects_plots, Parameter.
         Impact.no_effects


     Properties
     ----------

     base_type:
         Type of this parameter
    """

    _pattern = None  # laizy init.
    base_type: Type[ParameterBaseType] = str
    """Type of this parameter."""

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
        """Creates a Parameter with the following information."""
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

    def synchronize(self, tool: str) -> int:
        """Read the id of a tool from the database

        Parameters
        ----------
        tool:
            name of the plugin that is synchronised.

        Returns
        -------
        int:
            database id entry for the plugin
        """
        if self.id is None:
            itype = self.__class__.__name__
            tool_obj = Parameter.objects.get_or_create(
                tool=tool,
                version=self.version,
                mandatory=self.mandatory,
                default=self.default,
                impact=self.impact,
                parameter_name=self.name,
                parameter_type=itype,
            )
            self.id = tool_obj[0].id
        return self.id

    def _verified(
        self,
        orig_values: Any,
    ) -> Any:
        """Check if given values are valid."""

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

            self._pattern = re.compile(self.regex)

        if self._pattern:
            for val in values:
                if isinstance(val, str) and not self._pattern.search(val):
                    raise ValidationError("Invalid Value: %s" % val)

        # so it works transparent
        return orig_values

    def to_str(self, value: Any) -> str:
        """Transform this value in a serializable string.

        Parameters
        ----------
        value: Any
            Value that is to be converted to a string

        Returns
        -------
        str:
            String representation of the input value.
        """
        if self.max_items > 1:
            if not isinstance(value, list):
                value = [value]
            if self.item_separator is not None:
                return self.item_separator.join(value)
            else:
                # assume is a json array:
                return json.dumps(value)

        else:
            return str(value)

    def parse(
        self, value: Union[str, list[str]]
    ) -> Union[list[ParameterBaseType], ParameterBaseType]:
        """Parse a parameter value.

        Parameters
        ----------
        value: Union[str, list[str]]
            The parameter value that should be parsed.

        Returns
        -------
        ParameterBaseType:
            Parsed parameter value
        """
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

    def format(self, value: Optional[str] = None) -> str:
        """Format the default value or the given one to a string.

        Parameters
        ----------
        value: Optional[str], default: None
            the value to be formated, if set to None the default value
            of this paramter will be used.

        Returns
        -------
        str:
            formatted string value


        .. note::

            This can be overwriten to provide more control over how values are
            being displayed.
        """
        if value is None:
            if self.default is None:
                return "<undefined>"
            value = self.default
        return self.print_format % value

    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def infer_type(value: Any) -> Type:
        """Infer the type of a given default."""
        if isinstance(value, type):
            this_type = value
        else:
            this_type = type(value)
        if this_type in _type_mapping:
            return _type_mapping[this_type]()
        raise ValueError("Can't infer type for default '%s'." % value)

    def get_type(self) -> str:
        """Get the name of the class."""

        return self.__class__.__name__


class ParameterDictionary(dict):
    """Directory holding all plugin parameters for a ``Freva`` plugin.

    This class behaves like a built-in ``dict`` with additional features.
    The most prominent feature is that the order of added items is preseverd,
    as opposed to a normal build-in ``dict``.

    Parameters
    ----------
    parameters: :class:`ParameterType`
        collection of parameters of type :class:`ParameterType`.
        Note: The order of the parameters will be preseverd.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.String(name="title", default="The title"),
                parameters.Integer(name="int_value", mandatory=True),
                parameters.Float(name="float_value", default=0.0)
            )

    """

    def __init__(self, *parameters: ParameterType) -> None:
        """Instantiate ParameterDictionary with the given list of parameters."""
        super().__init__()
        extra = config.get_section("scheduler_options").get("extra_options", "").strip()
        if extra.lower() == "none":
            extra = ""
        extra_scheduler_options = String(
            "extra_scheduler_options",
            default=extra,
            help=(
                "Set additional options for the job submission to the "
                "workload manager (, seperated). Note: batchmode and web only."
            ),
        )
        self._params: dict[str, ParameterType] = dict()
        for param in parameters:
            # check name is unique
            if param.name in self._params:
                raise ValueError(
                    "Parameters name must be unique. Got second %s key." % param.name
                )
            self._params[param.name] = param
            self[param.name] = param.default
        self.setdefault("extra_scheduler_options", extra)
        self._params.setdefault("extra_scheduler_options", extra_scheduler_options)

    def __str__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join(
                ["%s<%s>: %s" % (k, self._params[k], v) for k, v in self.items()]
            ),
        )

    def get_parameter(self, param_name: str) -> ParameterType:
        """Return the parameter object from the given name.

        Parameters
        ---------

        param_name: str
            Name of the parameter that is queried

        Raises
        ------

        ValidationError:
            if the parameter name doesn't match anything stored here.

        """
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

    def parameters(self) -> list[ParameterType]:
        """All parameters stored in :class:`ParameterDictionary`"""
        return list(self._params.values())

    def _complete(
        self,
        config_dict: Optional[dict[str, Any]] = None,
        add_missing_defaults: bool = False,
    ) -> dict[str, Any]:
        """Completes a given dictionary with default values if required."""
        config_dict = config_dict or {}
        for key in set(self) - set(config_dict):
            if add_missing_defaults or self._params[key].default is not None:
                self._params[key].is_default = True
                default_param = self._params[key].default
                config_dict[key] = default_param
        return config_dict

    def validate_errors(
        self,
        config_dict: dict[str, Any],
        raise_exception: bool = False,
    ) -> dict[str, list[tuple[str, int]]]:
        """Checks if the given configuration dictionary is valied.

        Parameters
        ----------
        config_dict:
            the dictionary validated.
        raise_exception:
            If an exception should be risen. In such a case only a
            message is elevated (this could be changed)

        Returns
        -------
        dict:
            a dictionary with missing items and those having to manay of them or

        Raises
        ------
        ValidationError:
            If parameters are missing/duplicated and a `raise_exception` flag is
            set to `True`.
        """
        missing: list[tuple[str, int]] = []
        too_many_items: list[tuple[str, int]] = []
        for key, param in self._params.items():
            if param.mandatory and config_dict.get(key) is None:
                missing.append((key, param.max_items))
            default_value = config_dict.get(key, [])
            if not isinstance(default_value, list):
                default_value = [default_value]
            if len(default_value) > param.max_items:
                too_many_items.append((key, param.max_items))
        if missing or too_many_items:
            if raise_exception:
                msg = "Error found when parsing parameters. "
                if missing:
                    missing_values = [value for (value, _) in missing]
                    msg += "Missing mandatory parameters: %s" % ", ".join(
                        missing_values
                    )
                if too_many_items:

                    msg += "Too many entries for these parameters: %s" % ", ".join(
                        [
                            "%s(max:%s, found:%s)"
                            % (param, max, len(config_dict[param]))
                            for param, max in too_many_items
                        ]
                    )
                raise ValidationError(msg)
            return dict(missing=missing, too_many_items=too_many_items)
        return {}

    @deprecated_method("ParameterDictionary", "parse_arguments")
    def parseArguments(
        self, *args, **kwargs
    ) -> dict[str, Union[ParameterBaseType, list[ParameterBaseType]]]:
        """Deprecated version of the :class:`parse_arguments` method.

        :meta private:
        """
        return self.parse_arguments(*args, **kwargs)

    def parse_arguments(
        self,
        opt_arr: Union[str, list[str]],
        use_defaults: bool = False,
        complete_defaults: bool = False,
        check_errors: bool = True,
    ) -> dict[str, Union[ParameterBaseType, list[ParameterBaseType]]]:
        """Parse a list of strings to a parameter dictionary.

        The strings are of the type: ``key1=val1`` or ``key2``
        multiple values can be defined by either defining the same key
        multiple times or by using the item_separator character

        Parameters
        ----------
        opt_arr: Union[str, list[str]]
            List of strings containing
            ("key=value"|"key"|"key=value1,value2" iff item_separator==',')
        use_defaults: bool, default: False
            If the parameters defaults should be used when value is missing
        complete_defaults: bool, default: False
            Return a complete configuration containing None for those not
            provided parameters that has no defaults.
        check_errors: bool, default: True
            Check for configuration errors.

        Returns
        -------
        dict[str, Union[ParameterBaseType, list[ParameterBaseType]]:
            dictionary holding the plugin configuration.

        Raises
        ------
        ValidationError:
            Raises a ValidationError if a wrong configuration was parsed.

        """
        param_config: dict[str, Any] = defaultdict(list)
        if not isinstance(opt_arr, (list, tuple, set)):
            opt_arr = [opt_arr]
        for option in opt_arr:
            key, _, value = [key.strip() for key in option.partition("=")]
            value = value or "true"
            try:
                parsed_values: Any = self._params[key].parse(value)
            except KeyError as error:
                raise ValidationError(f"{key} is not a valid parameter") from error
            if isinstance(parsed_values, list):
                if isinstance(param_config[key], list):
                    param_config[key] = param_config[key] + parsed_values
                else:
                    param_config[key] = [param_config[key]] + parsed_values
            elif key not in param_config:
                param_config[key] = parsed_values
            elif not isinstance(parsed_values, list):
                param_config[key] = [param_config[key]] + [parsed_values]
            else:
                param_config[key].append(parsed_values)
        if use_defaults:
            self._complete(param_config, add_missing_defaults=complete_defaults)
        if check_errors:
            self.validate_errors(param_config, raise_exception=True)
        return param_config

    def get_help(self, width: int = 80) -> str:
        """Render plugin help string to be displayed in a cli context.

        Parameters
        ----------
        width: int, default 80
            Column width used to wrap the help text.

        Returns
        -------
        str:
            Help test for this plugin configuration.
        """

        help_str: list[str] = []
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
        return "\n".join(help_str)

    def synchronize(self, tool: str) -> None:
        """Synchronize all entries for a plugin configuration of a given tool

        Parameters
        ----------
        tool: str
            Name of the tool to be synced
        """

        for entry in self._params.values():
            entry.synchronize(tool)


class String(ParameterType):
    """A simple string parameter.

    Parameters
    ----------
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.String(
                            name="plot_tile",
                            mandatory=True,
                            default="Plot title",
                            help="Set a title for the plot"
                            ),
            )


    """

    base_type = str


class Integer(ParameterType):
    """An integer parameter.

    Parameters
    ----------
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.Integer(
                            name="const",
                            default=3,
                            help="Set a constant factor"
                            ),
            )


    """

    base_type = int

    def __init__(self, **kwargs):
        kwargs["regex"] = r"^[+-]?[0-9]+$"
        super().__init__(**kwargs)


class Float(ParameterType):
    """A float parameter.

    Parameters
    ----------
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.Float(
                            name="mul",
                            default=3.16,
                            help="Set a multiply factor."
                            ),
            )

    """

    base_type = float

    def __init__(
        self,
        **kwargs,
    ):
        kwargs[
            "regex"
        ] = r"^[+-]?(?:[0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)(?:[eE][+-]?[0-9]+)?$"
        super().__init__(**kwargs)


class File(String):
    """A parameter representing a file in the system.

    Parameters
    ----------
    file_extension: str, default: nc
        Suffix (file types) of the files that should be considered.
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.File(
                            name="input_file",
                            file_extension="geojson",
                            mandatory=False,
                            help="Select a geojson file.",
                            ),
            )

    """

    def __init__(self, file_extension="nc", **kwargs):
        self.file_extension = file_extension
        super().__init__(**kwargs)


class Directory(String):
    """A parameter representing a directory in the system. Deprecated

    :meta private:
    """

    def __init__(self, impact=Parameter.Impact.no_effects, **kwargs):
        super().__init__(impact=impact, **kwargs)


class InputDirectory(String):
    """A parameter representing a input directory in the system.

    Parameters
    ----------
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.InputDirectory(
                            name="input_directory",
                            default="/work/data",
                            mandatory=False,
                            help="Select the input directory",
                            ),
            )

    """


class CacheDirectory(Directory):
    """A parameter representing a cache directory in the system.

    Parameters
    ----------
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.CacheDirectory(
                            name="cache_directory",
                            default="/scratch",
                            help="Set the path to a temporary directory",
                            ),
            )

    """


class Date(String):
    """A date parameter.

    Parameters
    ----------
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.Date(
                            name="time",
                            default="1950-01-10",
                            help="Select a timestamp",
                            ),
            )

    """

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)


class Bool(ParameterType):
    """A boolean parameter.

    Parameters
    ----------

    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.Bool(
                            name="convert_variables",
                            default=True,
                            help="Convert the variables",
                            ),
            )

    """

    base_type = bool

    def parse(self, value: Any) -> bool:
        """Convert a string to a boolean value.

        The following values will be mapped

          true, t, yes, y, on, 1 => TRUE
          false, f, no, n, off, 2 => FALSE

        Parameters
        ----------

        value: Union[str, int, bool]
            Input representation of the boolean such as
            true, false, t, y, f, ...


        Raises
        ------
        ValidationException:
            if the given input value can not be converted to a bool.
        """

        if isinstance(value, bool):
            # it was no bool after all...
            return value
        if isinstance(value, str) and value:
            if value.lower() in ["true", "t", "yes", "y", "on", "1"]:
                return True
            if value.lower() in ["false", "f", "no", "n", "off", "0"]:
                return False
        elif isinstance(value, int):
            return bool(value)
        # if here we couldn't parse it
        raise ValueError(f"'{value}' is can't be converted to a boolean")


_type_mapping = {str: String, int: Integer, float: Float, bool: Bool}
"""These are the mapping of the default Python types to those of this framework.
This is mapping is used by the infer_type function to infer the type of a
given parameter default."""


class Range(String):
    """
    A range parameter, e.g passing experiment lists (1970,1975,...,2000).

    Parameters
    ---------

    see :class:`ParameterType` parameters for more details.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.Range(
                            name="time_range",
                            default="1950:10:1980", # range(1950, 1990, 10)
                            help="Set a time range",
                            ),
            )

    """

    def __init__(self, *args, **kwargs):
        # set max_items to a very large number...
        kwargs["max_items"] = 1e20
        self.base_type = int  # self.PrintableList
        super().__init__(*args, **kwargs)

    def _parse_colon(self, string: str) -> list[int]:
        """
        Parse colon separated strings.

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

    def _parse_comma(self, string: str) -> list[int]:
        """
        Parses comma separated strings and checks each part for colon
        separated strings

        Parameters
        ----------

        string: str
            comma seperated values that are converted to list

        Returns
        -------

        list[int]:
            list with integers
        """
        parts = string.split(",")
        res_list = list()
        for part in parts:
            res_list += self._parse_colon(part)
        return res_list

    def parse(self, value: Any) -> PrintableList:
        """
        Parses a "RangeString" and returns a "PrintableList".

        Values can be a comma separated string, colon separated or a combination
        Values after "-" are deleted from the resulting list

        Parameters
        ----------
        value: 'start:step:stop-value' --> 1970:5:2000-1985 or 1970:2000,1980-1990:1995


        Returns
        -------
        PrintableList:
            PrintableList of range items

        Raises
        ------
        ValueError:
            Raises a ValueError if items can't be parsed to list.
        """
        try:
            main_parts = value.split("-")
            result = self._parse_comma(main_parts[0])
            del_list = PrintableList()
            for part in main_parts[1:]:
                del_list += self._parse_comma(part)
            return PrintableList(sorted([x for x in result if x not in del_list]))
        except AttributeError as err:
            raise ValueError(f"'{value}' is no recognized as a range value") from err

    def to_str(self, value: Any) -> str:
        """Conevert input value to string."""
        return str(value)


class Unknown(String):
    """An unknown parameter for conversions.

    Parameters
    ---------
    see :class:`ParameterType` parameters for more details.
    """

    def __init__(
        self, impact=Parameter.Impact.affects_values, mandatory=True, **kwargs
    ):
        super().__init__(impact=impact, mandatory=mandatory, **kwargs)


class SolrField(String):
    """
    A parameter using solr for finding valid values.

    Parameters
    ---------
    facet: str
        Solr search facet used for this parameter
    group: int, default: 1
        The group this search facet belongs to. This can be used to group
        different search facets together, for example for comparing
        multi model ensemble
    multiple: bool, default: False
        flag indicating whether multiple facets are allowed.
    predefined_facets: Optional[list[str]], default: None
        a list of strings that are set as default search facets
    editable:
        flag indicating whether or not the value can be changed.
    kwargs:
        additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.SolrField(
                                name="variable_name",
                                default="tas",
                                facet="variable",
                                max_items=1,
                                group=2,
                                predefined_facets={"time_frequency":["1hr"]},
                                help="Select the variable name",
                            ),
            )

    """

    def __init__(
        self,
        *args,
        facet: Optional[str] = None,
        group: int = 1,
        multiple: bool = False,
        predefined_facets: Optional[list[str]] = None,
        editable: bool = True,
        **kwargs,
    ):
        if not facet:
            raise TypeError("`facet` must not be empty")
        self.facet = facet
        self.group = group
        self.multiple = multiple
        self.predefined_facets = predefined_facets
        self.editable = editable
        super().__init__(*args, **kwargs)


class SelectField(String):
    """Select field to select parameter from predefined vlaues.

    Parameters
    ----------
    options: dict[str, str]
        Directory representing the names and values of the predefined options.
    kwargs:
        Additional :class:`ParameterType` parameters.

    Example
    -------

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __parameters__ = parameters.ParameterDictionary(
                parameters.SelectField(
                                    name="options",
                                    default="first",
                                    options={1: "first", 2: "second"}
                                    help="Select from options",
                                      ),
            )

    """

    def __init__(self, options: dict[str, str], *args, **kwargs):
        self.options = options
        super().__init__(*args, **kwargs)

    def _verified(self, orig_values):

        if orig_values not in self.options.values():
            values = ",".join(list(self.options.values()))
            raise ValueError(
                f'Only the following values are allowed for "{self.name}": {values}'
            )
        return orig_values

    def parse(self, value: Any) -> str:
        """Parse a parameter value.

        Parameters
        ----------
        value: Union[str, list[str]]
            The parameter value that should be parsed.

        Returns
        -------
        ParameterBaseType:
            Parsed paramter value

        Raises
        ------
        ValueError:
            if value is not part of possible options.
        """

        if self._verified(value):
            for key, val in self.options.items():
                if value == val:
                    return key
        return ""
