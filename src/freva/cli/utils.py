"""Collection of utilities of the freva command line argument parser."""

from __future__ import annotations

import abc
import argparse
import logging
import os
import sysconfig
from copy import copy
from pathlib import Path
from typing import Optional, Type

import lazy_import

from evaluation_system.misc import FrevaLogger, logger

freva = lazy_import.lazy_module("freva")
config = lazy_import.lazy_module("evaluation_system.misc.config")


def get_cli_class(name: str) -> Optional[Type[BaseParser]]:
    """Get core module or cli extension.

    Parameters
    ----------
    name: str
        name of the cli sub module that is to be imported. This can be
        either a cli sub module for the freva core (databrowser, plugin etc)
        or an extension. Extensions are assumed to follow the following nameing
        conventions: :py:mod:`<name>.app`. The ``app`` sub module must contain
        a class named :py:class:`Cli`.

    Returns
    -------
    module: The imported module
    """
    mod_name = name.replace("-", "_")
    try:  # First try importing the freva core functionality
        mod = __import__(f"freva.cli.{mod_name}", fromlist=[""])
    except ImportError:
        try:  # Then additional modules
            mod = __import__(f"{mod_name}.cli", fromlist=[""])
        except ImportError:
            return None
    if hasattr(mod, "Cli") and hasattr(mod.Cli, "desc"):
        return mod.Cli
    return None


class BaseParser(metaclass=abc.ABCMeta):
    """Base class that is used to construct a valid freva cli tool.

    This class can be used to extent the freva commands with additional sub
    commands.

    Parameters
    ----------
    parser: argparse.ArgumentParser, default: None
        Already parsed arguments if, None given (default) a new
        :py:class:`ArgumentParser` will should be constructed.

    Attributes
    ----------
    desc: str
        The class should have the :py:attribute:`desc` attribute set. This
        attribute is used to display a short summary over what this command
        is supposed to do.


    Example
    -------
    Suppose your tool named ``mytool`` should be made a freva cli extension the
    then the ``mytool`` library should define a command line interface that
    resides in the ``mytool.cli`` sub module of ``mytool``. Additionally your
    ``mytool.cli`` sub module has to define a class called ``Cli``. The content
    of the ``Cli`` class could like the following:

    .. code-block:: python

        import argparse
        from pathlib import Path
        import sys
        from typing import Optional

        from ferva.cli import BaseParser

        class Cli(BaseParser):

            desc = "Apply mytool."

            def __init__(parser: Optional[argparse.ArgumentParser] = None):

                super().__init__("mytool", parser)
                self.parser.add_argument("path",
                                         type=Path,
                                         help="The first argument"
                )

            def do_something(path: Path) -> list[str]:
                '''Do the actual work, for example list a directory.'''
                return sorted(path.iterdir())

        def main():
            '''The main method calling the cli from a stand alone tool.'''

            arg_p = Cli()
            args = arg_p.parse_args(sys.argv[1:])
            arg_p.do_something(args.path)

    Following this outline all that would be needed to do is creating an entry
    point named ``freva-mytool`` pointing to ``mytool.cli:main``. This would
    be sufficent to creagte a freva mytool sub command.
    """

    desc: str = ""
    """The short describtion of a freva command."""

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
        command: str = "freva",
    ):
        self.logger.is_cli = True
        self.parser = parser or argparse.ArgumentParser(
            prog=command,
            description=self.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

    @property
    def logger(self) -> FrevaLogger:
        """Use evaluation_system logger in all classes using ths class."""
        return logger

    def set_debug(self, debug: bool) -> None:
        """Set the logger level to DEBUG."""
        if debug is True:
            self.logger.setLevel(logging.DEBUG)

    def parse_args(self, argv: Optional[list[str]] = None) -> argparse.Namespace:
        """Parse the command line arguments."""
        args, unknown = self.parser.parse_known_args(argv)
        for arg in unknown:
            if arg.startswith("-"):
                self.parser.error(f"Unknown option: {arg}")
        self.kwargs = {k: v for (k, v) in args._get_kwargs() if k != "apply_func"}
        if unknown:
            self.kwargs["unknown"] = unknown
        self.set_debug(self.kwargs.pop("debug", False))
        return args


class SubCommandParser(BaseParser):
    """Base class for all freva sub command line argument parsers."""

    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
        sub_parsers: Optional[dict[str, Type[BaseParser]]] = None,
        command: str = "freva",
    ) -> None:
        """Create the sub-command parsers."""
        super().__init__(parser, command)
        self.subparsers = self.parser.add_subparsers(help="Available sub-commands:")
        self.sub_commands = sub_parsers or self.get_subcommand_parsers()
        self.help = self.get_subcommand_help(self.sub_commands)
        for cmd, subparser in self.sub_commands.items():
            self.parse_subcommand(cmd, subparser)

    def parse_subcommand(self, command: str, cli_class: Type[BaseParser]) -> None:
        """Parse the databrowser command."""

        call_parsers = self.subparsers.add_parser(
            command,
            description=cli_class.desc,
            help=cli_class.desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        cli_class(call_parsers)

    def _usage(self, *args: Optional[str], **kwargs: Optional[str]) -> None:
        """Exit with usage message."""
        self.parser.error(
            "the following sub-commands are "
            f"required: {', '.join(self.sub_commands.keys())}"
        )

    @staticmethod
    def get_subcommand_parsers() -> dict[str, Type[BaseParser]]:
        """Create the help strings of the available sub commands."""
        path_list = [
            Path(p)
            for p in (os.environ.get("PATH") or os.defpath).split(os.pathsep)
            + [sysconfig.get_paths().get("scripts", "")]
            if p and Path(p).is_dir()
        ]
        parsers = {}
        for _dir in path_list:
            for file in _dir.iterdir():
                if file.name.startswith("freva-"):
                    _, _, sub_cmd = file.name.partition("-")
                    if sub_cmd not in parsers:
                        parser_class = get_cli_class(sub_cmd)
                        if parser_class is not None:
                            parsers[sub_cmd] = parser_class
        return parsers

    @classmethod
    def get_subcommand_help(
        cls,
        parsers: Optional[dict[str, Type[BaseParser]]] = None,
    ) -> dict[str, str]:
        """Create the help strings of the available sub commands."""
        parsers = parsers or cls.get_subcommand_parsers()
        return {h: mod.desc for (h, mod) in parsers.items() if hasattr(mod, "desc")}


class BaseCompleter:
    """Base class for command line argument completers."""

    def __init__(
        self,
        metavar: str,
        argv: list[str],
        choices: Optional[dict[str, tuple[str, str]]] = None,
        shell: str = "bash",
        strip: bool = False,
        flags_only: bool = False,
    ):
        self.choices = choices or {}
        self.strip = strip
        self.metavar = metavar
        self.argv = argv
        self.flags_only = flags_only
        if shell == "zsh":
            self.get_print = self._print_zsh
        elif shell == "fish":
            self.get_print = self._print_fish
        else:
            self.get_print = self._print_default

    def _print_zsh(self, choices: dict[str, tuple[str, str]]) -> list[str]:
        out = []
        for key, (_help, func) in choices.items():
            if self.metavar != "databrowser" or key.startswith("-"):
                out.append(f"{key}[{_help}]{func}")
            else:
                out.append(f"{key}: {_help}")
        return out

    def _print_fish(self, choices: dict[str, tuple[str, str]]) -> list[str]:
        out = []
        for key, (_help, func) in choices.items():
            out.append(f"{key}: {_help}")
        return out

    def _print_default(self, choices: dict[str, tuple[str, str]]) -> list[str]:
        out = []
        for key, (_help, _) in choices.items():
            if self.metavar == "databrowser" and not key.startswith("-"):
                out.append(f"{key}: {_help}")
            else:
                out.append(key)
        return out

    def _get_databrowser_choices(self) -> dict[str, tuple[str, str]]:
        """Get the choices for databrowser command."""

        facet_args = []
        for arg in self.argv:
            if len(arg.split("=")) == 2:
                facet_args.append(arg)
        facets = BaseCompleter.arg_to_dict(facet_args)
        search = freva.facet_search(**facets)
        choices = {}
        for att, values in search.items():
            if att not in facets:
                keys = ",".join([v for n, v in enumerate(values)])
                choices[att] = (keys, "")
        return choices

    def _get_plugin_choices(self) -> dict[str, tuple[str, str]]:
        """Get the choices for the plugin command."""

        docs: dict[str, dict[str, str]] = {}
        desc: dict[str, dict[str, str]] = {}
        plugins: dict[str, str] = {}
        try:
            plugin_cache = freva.read_plugin_cache()
        except Exception:
            plugin_cache = []
        for plugin in plugin_cache:
            plugins[plugin.name] = plugin.description
            docs[plugin.name] = {}
            desc[plugin.name] = {}
            for param, doc, value in plugin.parameters:
                desc[plugin.name][param] = doc
                docs[plugin.name][param] = value
        args = [arg for arg in self.argv if not arg.startswith("-") and arg != "plugin"]
        choices = {}
        if not args:
            # No plugin name was given
            return {pl: (help, "") for pl, help in plugins.items()}
        try:
            plugin_config = docs[args[0]]
            setup = desc[args[0]]
        except KeyError:
            # Wrong plugin name
            return {}
        options = []
        for key in plugin_config.keys():
            option_present = False
            for arg in args:
                if arg.startswith(f"{key}="):
                    option_present = True
                    break
            if not option_present:
                options.append(f"{key}=")
        for option in options:
            opt = option.strip("=")
            if "file" in setup[opt].lower() or "dir" in setup[opt].lower():
                choices[opt] = (setup[opt], ":file:_files")
            else:
                choices[opt] = (setup[opt], "")
        return choices

    @property
    def command_choices(self) -> dict[str, tuple[str, str]]:
        """Get the command line arguments for all sub commands."""

        choices = {}
        if self.flags_only:
            return self.choices
        if self.metavar == "databrowser":
            choices = self._get_databrowser_choices()
        elif self.metavar == "plugin":
            choices = self._get_plugin_choices()
        return {**self.choices, **choices}

    def formated_print(self) -> None:
        """Print all choices to be processed by the shell completion function."""

        out = self.get_print(self.command_choices)
        for line in out:
            if line.startswith("-") and self.strip and not self.flags_only:
                continue
            elif not line.startswith("-") and self.flags_only:
                continue
            print(line)

    @staticmethod
    def arg_to_dict(
        args: Optional[list[str]], append: bool = False
    ) -> dict[str, list[str]]:
        """Convert a parsed arguments with key=value pairs to a dictionary.

        Parameters:
        ----------
        args:
            Collection of arguments that are converted to dict, the arguments
            should be of form key=value
        append:
            If a key occurs twice convert first value to list and append second
            value to list, the default behaviour is updating the entry with
            the second value
        Returns:
        --------
        dict: Dictionariy representation of key=value pairs
        """
        out_dict: dict[str, list[str]] = {}
        for arg in args or []:
            key, _, value = arg.partition("=")
            if append and key in out_dict:
                out_dict[key].append(value)
            else:
                out_dict[key] = [value]
        return out_dict

    @classmethod
    def _get_choices_from_parser(
        cls,
        parser: argparse.ArgumentParser,
        argv: list[str],
    ) -> dict[str, tuple[str, str]]:
        choices: dict[str, tuple[str, str]] = {}
        for action in parser._actions:
            action_type = ""
            if isinstance(action, argparse._SubParsersAction):
                if argv:
                    cmd = argv.pop(0)
                    sub_parser = action.choices.get(cmd, "")
                    if sub_parser:
                        choices.update(cls._get_choices_from_parser(sub_parser, argv))
                else:
                    for ch, _parser in action.choices.items():
                        choices[ch] = _parser.description or "", action_type
            if action.help == argparse.SUPPRESS:
                # This is an option that is not exposed to users
                continue
            if action.type == Path:
                action_type = ":file:_files"
            if action.option_strings:
                choice = action.option_strings[0]
            else:
                choice = action.dest
            if choice.lower() not in (
                "facet",
                "facets",
                "tool-name",
                "options",
                "tool-options",
                "==suppress==",
                "-h",
            ):
                choices[choice] = (action.help or "", action_type)
        return choices

    @classmethod
    def get_args_of_subcommand(cls, argv: list[str]) -> dict[str, tuple[str, str]]:
        """Get all possible arguments from a freva sub-command."""
        sub_command = argv.pop(0)
        parser_class = get_cli_class(sub_command)
        if parser_class is None:
            return {}
        cli_parser = parser_class()
        return cls._get_choices_from_parser(cli_parser.parser, argv)

    @classmethod
    def parse_choices(cls, argv: list[str]) -> BaseCompleter:
        """Create the completion choices from given cmd arguments."""
        parser = argparse.ArgumentParser(
            description="Get choices for command line arguments"
        )
        parser.add_argument(
            "command", help="First command, freva, freva-histor etc", type=str
        )
        parser.add_argument("--shell", help="Shell in use", default="bash", type=str)
        parser.add_argument(
            "--strip",
            help="Do not print options starting with -",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--flags-only",
            help="Only print options starting with -",
            default=False,
            action="store_true",
        )
        app, args = parser.parse_known_args(argv)
        main_choices = {
            k: (v, "") for k, v in SubCommandParser.get_subcommand_help().items()
        }
        if app.command == "freva" and not args:
            return cls(app.command, [], main_choices, shell=app.shell, strip=app.strip)
        if app.command != "freva":
            sub_cmd = "-".join(app.command.split("-")[1:])
            args.insert(0, sub_cmd)
        choices = {}
        if args[0] in main_choices:
            choices = cls.get_args_of_subcommand(copy(args))
        choices = {k: v for (k, v) in choices.items() if k not in args}
        return cls(
            args[0],
            args,
            choices,
            shell=app.shell,
            strip=app.strip,
            flags_only=app.flags_only,
        )


def print_choices(arguments: list[str]) -> None:
    """Print completion choices based of command line arguments.

    Parameters:
    -----------
    arguments:
        List of command line arguments, that are evaluated by the choice printer
    """
    argv = [arg.strip() for arg in arguments if arg.strip()]
    comp = BaseCompleter.parse_choices(argv)
    comp.formated_print()
