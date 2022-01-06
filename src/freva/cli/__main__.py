"""Module to print command argument line argument choices."""

import sys
from typing import List
from .utils import BaseCompleter


def proc_databrowser(argv: List[str], choices: List[str]) -> List[str]:
    """Get the choices for databrowser command."""
    from freva import databrowser
    facet_args = []
    for arg in argv:
        try:
            key, value = arg.split("=")
        except ValueError:
            continue
        if value and key:
            facet_args.append(arg)
    facets = BaseCompleter.arg_to_dict(facet_args)
    search = databrowser(attributes=False, all_facets=True, **facets)
    for facet in facets.keys():
        search.pop(facet)
    try:
        key, value = argv[-1].split("=")
    except ValueError:
        value = None
    try:
        if not value.strip():
            return search[key]
    except KeyError:
        return []
    except AttributeError:
        pass
    return choices + [f"{key}=" for key in search.keys()]


def proc_plugin(argv: List[str], choices: List[str]) -> List[str]:
    """Get the choices for the plugin command."""
    from freva._plugin import list_plugins
    from evaluation_system.api import plugin_manager as pm

    docs = {}
    for plugin in list_plugins():
        docs[plugin] = dict(pm.getPluginInstance(plugin).__parameters__.items())
    args = [arg for arg in argv if not arg.startswith('-') and arg != "plugin"]
    if not args:
        # No plugin name was given
        choices += list(docs.keys())
    else:
        # We have at lease one plugin name
        try:
            config = docs[args[0]]
        except KeyError:
            # Wrong plugin name
            return []
        options = []
        for key in config.keys():
            option_present = False
            for arg in args:
                if arg.startswith(f"{key}="):
                    option_present = True
                    break
            if not option_present:
                options.append(f"{key}=")
        choices = options
    return choices


def main() -> None:
    argv = sys.argv[1:]
    comp = BaseCompleter.parse_choices(argv)
    if not comp.choices:
        return
    choices = comp.choices
    if comp.metavar == "databrowser":
        choices = proc_databrowser(argv, choices)
    elif comp.metavar == "plugin":
        choices = proc_plugin(argv, choices)
    print(" ".join(choices))


main()
