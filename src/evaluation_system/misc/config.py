"""
.. moduleauthor:: Sebastian Illing / estani

This module manages the central configuration of the system.
"""
from __future__ import annotations
from typing import Optional, Sequence

import os
import os.path as osp
from pathlib import Path
import hashlib
import requests
from configparser import ConfigParser, NoSectionError, ExtendedInterpolation
import sys
import warnings
import toml

import appdirs
from evaluation_system.misc.utils import Struct, TemplateDict
from evaluation_system.misc import (
    logger as log,
    CONFIG_FILE,
    _DEFAULT_CONFIG_FILE_LOCATION,
)
from evaluation_system.misc.exceptions import ConfigurationException

DIRECTORY_STRUCTURE = Struct(LOCAL="local", CENTRAL="central", SCRATCH="scratch")
"""Type of directory structure that will be used to maintain state::

    local   := <home>/<base_dir>...
    central := <base_dir_location>/<base_dir>/<user>/...
    scratch := <base_dir_location>/<user>/<base_dir>...

We only use local at this time, but we'll be migrating to central in
the future for the next project phase."""
# Some defaults in case nothing is defined
USER_CONFIG_FILE_LOC = osp.join(
    appdirs.user_config_dir(), "freva", "evaluation_system.conf"
)
if Path(USER_CONFIG_FILE_LOC).exists():
    _DEFAULT_CONFIG_FILE_LOCATION = USER_CONFIG_FILE_LOC
EVALUATION_SYSTEM_HOME = (os.sep).join(osp.abspath(__file__).split(osp.sep)[:-4])
SPECIAL_VARIABLES = TemplateDict(EVALUATION_SYSTEM_HOME=EVALUATION_SYSTEM_HOME)

_DEFAULT_DRS_CONFIG_FILE = os.environ.get(
    "EVALUATION_SYSTEM_DRS_CONFIG_FILE",
    osp.abspath(osp.join(CONFIG_FILE, osp.pardir, "drs_config.toml")),
)
_PUBLIC_KEY_DIR = Path(CONFIG_FILE).parent
#: config options
BASE_DIR = "base_dir"
"The name of the directory storing the evaluation system (output, configuration, etc)"

ROOT_DIR = "root_dir"

DIRECTORY_STRUCTURE_TYPE = "directory_structure_type"
"""Defines which directory structure is going to be used.
See DIRECTORY_STRUCTURE"""

BASE_DIR_LOCATION = "base_dir_location"
"""The location of the directory defined in $base_dir."""

DATABASE_TIMEOUT = 2
"""Time out in seconds for the SQLite database"""

SCHEDULER_WAITING_TIME = 3
"""
Waiting time in seconds before the scheduler runs the job
We suggest: DATABASE_TIMEOUT+1
"""

SCRATCH_DIR = "scratch_dir"
""" The scratch dir of the user """


SCHEDULER_OUTPUT_DIR = "scheduler_output_dir"
""" Determines the folder the SLURM output files will be saved in """

SCHEDULER_INPUT_DIR = "scheduler_input_dir"
"""
Determines the folder the SLURM input files will be saved in.
This variable is  read by the User object,
use always user.getUserSchedulerInputDir()!
"""

# SCHEDULER_COMMAND='/client/bin/sbatch'
""" The command for the scheduler """

SCHEDULER_OPTIONS = "--begin=now+" + str(SCHEDULER_WAITING_TIME)

NUMBER_OF_PROCESSES = 24

DATABASE_FILE = "database_file"
""" Determines the path of the database file """

# config file section
CONFIG_SECTION_NAME = "evaluation_system"
"""This is the name of the section in the configuration file where
the central configuration is being stored"""

#: Plugins *******************
PLUGINS = "plugin:"
"""Sections that start with this prefix are meant for configuring the plug-ins.
This keyword is also used for retrieving all plug-ins configurations."""

PLUGIN_PATH = "plugin_path"
""""Path to the plug-in's home"""

PLUGIN_PYTHON_PATH = "python_path"
"""Path to the plug-in's python sources that should be added to
python's path when being run."""

PLUGIN_MODULE = "module"
"""The full qualified module name where the plug-in is implemented."""

PREVIEW_PATH = "preview_path"
"""path to preview pictures."""

GIT_BASH_STARTOPTIONS = "git_bash_startoptions"
"""We use -lc, use this option if something else is required"""

#: database #####################
DB_HOST = "db.host"
""" name of the database server """

DB_USER = "db.user"
""" database user """

DB_PASSWD = "db.passwd"
""" database password """

DB_DB = "db.db"
""" the database name on the server """

DB_PORT = "db.port"
""" database connection port"""

#: Solr #########################
SOLR_HOST = "solr.host"
"""Hostname of the Solr instance."""

SOLR_PORT = "solr.port"
"""Port number of the Solr instance."""

SOLR_CORE = "solr.core"
"""Core name of the Solr instance."""


_config = None
_drs_config = None

exclude: list[str] = ["extra_scheduler_options"]
"""This is a list of strings that excludes entries from being saved to
the history database entries."""


def _get_public_key(project_name: str) -> str:
    key_file = os.environ.get("PUBKEY", None) or _PUBLIC_KEY_DIR / f"{project_name}.crt"
    sha = ""
    try:
        with Path(key_file).open() as f:
            key = "".join([k.strip() for k in f.readlines() if not k.startswith("-")])
        sha = hashlib.sha512(key.encode()).hexdigest()
    except FileNotFoundError:
        warnings.warn(
            (
                f"{key_file} not found. Secrets are stored in central vault and a"
                "public key is needed to open the vault. Without the public key"
                " you won't be probaply be able to establish as database "
                "connection."
            ),
            category=Warning,
        )
    return sha


def _read_secrets(
    sha: str,
    key: str,
    *db_hosts: Sequence[str],
    port: int = 5002,
    protocol: str = "http",
) -> Optional[str]:
    """Query the vault for data database secrets, of a given key."""
    for db_host in db_hosts:
        url = f"{protocol}://{db_host}:{port}/vault/data/{sha}"
        try:
            req = requests.get(url).json()
        except (requests.exceptions.ConnectionError, requests.exceptions.InvalidURL):
            req = {}
        try:
            return req[key]
        except KeyError:
            pass
    return None


def reloadConfiguration() -> None:
    """Reloads the configuration.
    This can be used for reloading a new configuration from disk.
    At the present time it has no use other than setting different configurations
    for testing, since the framework is restarted every time an analysis is
    performed."""
    global _config
    _config = {
        BASE_DIR: "evaluation_system",
        BASE_DIR_LOCATION: os.path.expanduser("~"),
        DIRECTORY_STRUCTURE_TYPE: DIRECTORY_STRUCTURE.LOCAL,
        PLUGINS: {},
    }

    config_file = os.environ.get(
        "EVALUATION_SYSTEM_CONFIG_FILE", _DEFAULT_CONFIG_FILE_LOCATION
    )
    log.debug("Loading configuration file from: %s" % config_file)
    if config_file and os.path.isfile(config_file):
        config_parser = ConfigParser(interpolation=ExtendedInterpolation())
        with open(config_file, "r") as fp:
            config_parser.read_file(fp)
            if not config_parser.has_section(CONFIG_SECTION_NAME):
                raise ConfigurationException(
                    (
                        "Configuration file is missing section %s.\n"
                        + "For Example:\n[%s]\nprop=value\n..."
                    )
                    % (CONFIG_SECTION_NAME, CONFIG_SECTION_NAME)
                )
            else:
                _config.update(config_parser.items(CONFIG_SECTION_NAME))
                for plugin_section in [
                    s for s in config_parser.sections() if s.startswith(PLUGINS)
                ]:
                    _config[PLUGINS][
                        plugin_section[len(PLUGINS) :]
                    ] = SPECIAL_VARIABLES.substitute(
                        dict(config_parser.items(plugin_section))
                    )

                db_hosts = (
                    config_parser[CONFIG_SECTION_NAME]["db.host"],
                    config_parser[CONFIG_SECTION_NAME]["project_name"] + "_vault",
                )
                # This will look first for secrets set in the config file. It will only
                # load the public key for the vault if any are missing and it will only
                # look for the missing keys in the vault. Any keys set in the config
                # will take priority
                secret_store_keys: list[str] = []
                for secret in ("db.user", "db.passwd", "db.db", "db.host"):
                    value = _config.get(secret, None)
                    if value:
                        _config[secret] = value
                    else:
                        secret_store_keys.append(secret)
                if len(secret_store_keys) > 0:
                    secret_store_keys += ["db.port"]
                    sha: str = _get_public_key(
                        config_parser[CONFIG_SECTION_NAME]["project_name"]
                    )
                    for secret in secret_store_keys:
                        _config[secret] = _read_secrets(sha, secret, *db_hosts)
            log.debug("Configuration loaded from %s", config_file)
    else:
        log.debug(
            "No configuration file found in %s. Using default values.", config_file
        )

    _config = SPECIAL_VARIABLES.substitute(_config, recursive=False)
    # perform all special checks
    if not DIRECTORY_STRUCTURE.validate(_config[DIRECTORY_STRUCTURE_TYPE]):
        raise ConfigurationException(
            "value (%s) of %s is not valid. Should be one of: %s"
            % (
                _config[DIRECTORY_STRUCTURE_TYPE],
                DIRECTORY_STRUCTURE_TYPE,
                ", ".join(DIRECTORY_STRUCTURE.toDict().values()),
            )
        )


_nothing = object()


def get(config_prop, default=_nothing):
    """Returns the value stored for the given config_prop.
    If the config_prop is not found and no default value is provided an exception
    will be thrown. If not the default value is returned.

    :param config_prop: property for which it's value is looked for.
    :type config_prop: str
    :param default: If the property is not found this value is returned.
    :return: the value associated with the given property, the default one
    if not found or an exception is thrown if no default is provided."""
    if config_prop in _config:
        return _config[config_prop]
    elif default != _nothing:
        return default
    else:
        raise ConfigurationException("No configuration for %s" % config_prop)


def get_plugin(plugin_name, config_prop, default=_nothing):
    """Returns the value stored for the given config_prop at the given plugin.
    If the config_prop is not found and no default value is provided an exception
    will be thrown. If not the default value is returned. If the plug.in name does
    not exists an exception is thrown.

    :param plugin_name: name of an existing plug-in as returned by
    :class:`get`(:class:`PLUGINS`)
    :type plugin_name: str
    :param config_prop: property for which it's value is looked for.
    :type config_prop: str
    :param default: If the property is not found this value is returned.
    :return: the value associated with the given property, the default one
    if not found
        or an exception is thrown if no default is provided."""
    if plugin_name in _config[PLUGINS]:
        _plugin_config = _config[PLUGINS][plugin_name]
        if config_prop in _plugin_config:
            return _plugin_config[config_prop]
        elif default != _nothing:
            return default
        else:
            raise ConfigurationException(
                "No configuration for %s for plug-in %s" % (config_prop, plugin_name)
            )
    else:
        raise ConfigurationException("No plug-in named %s" % plugin_name)


def keys():
    """Returns all the keys from the current configuration."""
    return _config.keys()


def get_section(section_name, config_file=None):
    conf = ConfigParser(interpolation=ExtendedInterpolation())

    config_file = config_file or os.environ.get(
        "EVALUATION_SYSTEM_CONFIG_FILE", _DEFAULT_CONFIG_FILE_LOCATION
    )
    conf.read(config_file)
    try:
        section = dict(conf.items(section_name))
    except NoSectionError:
        raise NoSectionError(f'There is no "{section_name}" section in config file')
    return SPECIAL_VARIABLES.substitute(section)


def get_drs_config():
    global _drs_config
    if _drs_config is None:
        drs_config = os.environ.get(
            "EVALUATION_SYSTEM_DRS_CONFIG_FILE", str(_DEFAULT_DRS_CONFIG_FILE)
        )
        with open(drs_config, "r") as drs_file:
            _drs_config = toml.load(drs_file)
    return _drs_config
