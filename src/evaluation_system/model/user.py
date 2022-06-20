"""Manage the abstraction of a system user."""
from __future__ import annotations
import pwd
import os
from configparser import ConfigParser as Config, ExtendedInterpolation
from typing import Optional, Union

from evaluation_system.misc import config, utils
from evaluation_system.model.db import UserDB


class User:
    """
    This Class encapsulates a user (configurations, etc).

    Parameters
    ----------
    uid: int
        user id in the local system, if not provided the current user is used.
    email: str
        user's email address
    """

    CONFIG_DIR: str = "config"
    """The directory name where all plug-in/system configurations will be stored."""

    CACHE_DIR: str = "cache"
    """The temporary directory where plug-ins can store files while performing some computation."""

    OUTPUT_DIR: str = "output"
    """The directory where output files are stored. Intended for files containing data and thus taking much space."""

    PLOTS_DIR: str = "plots"
    """The directory where just plots are stored. Plots are assumed to be much smaller in size than data and might
therefore live longer"""

    PROCESSES_DIR: str = "processes"
    """The directory might handle information required for each running process."""

    EVAL_SYS_CONFIG: str = os.path.join(CONFIG_DIR, "evaluation_system.config")
    """The file containing a central configuration for the whole system (user-wise)"""

    EVAL_SYS_DEFAULT_CONFIG: str = os.path.normpath(
        os.path.dirname(__file__) + "/../../etc/system_default.config"
    )
    """The central default configuration file for all users. It should not be confused with the system configuration
file that is handled by :class:`evaluation_system.api.config`."""

    def __init__(self, uid: Optional[Union[int, str]] = None, email: str = ""):
        """Creates a user object for the provided id.

        If no id is given, a user object for
        the current user, i.e. the one that started the application, is created instead.
        """
        self._dir_type = config.get(config.DIRECTORY_STRUCTURE_TYPE)
        uid = uid or os.getuid()
        self._userdata = None
        if isinstance(uid, str):
            self._userdata = pwd.getpwnam(uid)
        else:
            self._userdata = pwd.getpwuid(uid)

        if self._userdata is None:
            raise Exception("Cannot find user %s" % uid)
        self._email = email
        self._userconfig = Config(interpolation=ExtendedInterpolation())
        # try to load teh configuration from the very first time.
        self._userconfig.read(
            [
                User.EVAL_SYS_DEFAULT_CONFIG,
                os.path.join(self._userdata.pw_dir, User.EVAL_SYS_CONFIG),
            ]
        )

        self._db = UserDB(self)

        row_id = self._db.getUserId(self.getName())

        if row_id:
            self._db.updateUserLogin(row_id, email)
        else:
            self._db.createUser(self.getName(), email=self._email)

    # $USER_BASE_DIR := central directory for this user in the evaluation system.
    # $USER_OUTPUT_DIR := directory where the output data for this user is stored.
    # $USER_PLOT_DIR := directory where the plots for this user is stored.
    # $USER_CACHE_DIR := directory where the cached data for this user is stored."""

    def __str__(self):
        return "<User (username:%s, info:%s)>" % (
            self._userdata[0],
            str(self._userdata[2:]),
        )

    def getUserConfig(self):
        """:returns: the user configuration object :py:class:`ConfigParser.SafeConfigParser`"""
        return self._userconfig

    def getUserDB(self):
        """:returns: the db abstraction for this user.
        :rtype: :class:`evaluation_system.model.db.UserDB`"""
        return self._db

    def reloadConfig(self):
        """Reloads user central configuration from disk (not the plug-in related one)."""
        self._userconfig = Config(interpolation=ExtendedInterpolation())
        self._userconfig.read(
            [
                User.EVAL_SYS_DEFAULT_CONFIG,
                os.path.join(self.getUserBaseDir(), User.EVAL_SYS_CONFIG),
            ]
        )
        return self._userconfig

    def writeConfig(self):
        """Writes the user central configuration to disk according to :class:`EVAL_SYS_CONFIG`"""

        fp = open(os.path.join(self.getUserBaseDir(), User.EVAL_SYS_CONFIG), "w")
        self._userconfig.write(fp)
        fp.close()

    def getName(self):
        """:returns: the user name
        :rtype: str"""
        return self._userdata.pw_name

    def getEmail(self):
        """
        :returns: user's email address. Maybe None. :rtype: str
        """
        return self._email

    def getUserID(self):
        """:returns: the user id.
        :rtype: int"""
        return self._userdata.pw_uid

    def getUserHome(self):
        """:returns: the path to the user home directory.
        :rtype: str"""
        return self._userdata.pw_dir

    def getUserScratch(self):
        """:returns: the path to the user's scratch directory.
        :rtype: str"""
        return self._getUserBaseDir()

    def _getUserBaseDir(self):
        if self._dir_type == config.DIRECTORY_STRUCTURE.LOCAL:
            return os.path.join(self.getUserHome(), config.get(config.BASE_DIR))
        else:
            return os.path.join(
                config.get(config.BASE_DIR_LOCATION),
                str(self.getName()),
                config.get(config.BASE_DIR),
            )

    def _getUserDir(self, dir_type, tool=None, create=False):
        base_dir = dict(
            base="",
            config=User.CONFIG_DIR,
            cache=User.CACHE_DIR,
            output=User.OUTPUT_DIR,
            plots=User.PLOTS_DIR,
            processes=User.PROCESSES_DIR,
            scheduler_in=config.get(config.SCHEDULER_INPUT_DIR),
            scheduler_out=config.get(config.SCHEDULER_OUTPUT_DIR),
        )

        if tool is None:
            bd = base_dir[dir_type]
            # concatenate relative paths only
            if bd and bd[0] == "/":
                dir_name = bd
            else:
                # return the directory where the tool configuration files are stored
                dir_name = os.path.join(self._getUserBaseDir(), bd)
        else:
            # It's too confusing if we create case sensitive directories...
            tool = tool.lower()
            # return the specific directory for the given tool
            dir_name = os.path.join(self._getUserBaseDir(), base_dir[dir_type], tool)

        # make sure we have a canonical path
        dir_name = os.path.abspath(dir_name)

        if create and not os.path.isdir(dir_name):
            # we are letting this fail in case of problems.
            utils.supermakedirs(dir_name, 0o0755)

        return dir_name

    def getUserBaseDir(self, **kwargs):
        """Returns path to where this system is managing this user data.

        :param kwargs: ``create`` := If ``True`` assure the directory exists after the call is done.
        :returns: (str) path"""
        return self._getUserDir("base", **kwargs)

    def getUserSchedulerInputDir(self, **kwargs):
        """Returns path to where this system is managing this user data.

        :param kwargs: ``create`` := If ``True`` assure the directory exists after the call is done.
        :returns: (str) path"""
        return self._getUserDir("scheduler_in", **kwargs)

    def getUserSchedulerOutputDir(self, **kwargs):
        """Returns path to where this system is managing this user data.

        :param kwargs: ``create`` := If ``True`` assure the directory exists after the call is done.
        :returns: (str) path"""
        return self._getUserDir("scheduler_out", **kwargs)

    def getUserToolConfig(self, tool, **kwargs):
        """Returns the path to the configuration file.

        :param kwargs: ``create`` := If ``True`` assure the underlaying directory exists after the call is done.
        :param tool: tool/plug-in for which the information is returned.
        :type tool: str
        :returns: path to the configuration file."""
        config_dir = self._getUserDir("config", tool, **kwargs)
        return os.path.join(config_dir, "%s.conf" % tool)

    def getUserConfigDir(self, tool=None, **kwargs):
        """Return the path to the directory where all configurations for this user are stored.

        :param kwargs: ``create`` := If ``True`` assure the  directory exists after the call is done.
        :param tool: tool/plug-in for which the information is returned. If None, then the directory
                     where all information for all tools reside is returned insted (normally, that would
                     be the parent directrory).
        :type tool: str
        :returns: path to the directory."""
        return self._getUserDir("config", tool, **kwargs)

    def getUserCacheDir(self, tool=None, **kwargs):
        """Return directory where cache files for this user (might not be "only" for this user though).

        :param kwargs: ``create`` := If ``True`` assure the  directory exists after the call is done.
        :param tool: tool/plug-in for which the information is returned. If None, then the directory
                     where all information for all tools reside is returned insted (normally, that would
                     be the parent directrory).
        :type tool: str
        :returns: path to the directory."""
        return self._getUserDir("cache", tool, **kwargs)

    def getUserProcessDir(self, tool=None, **kwargs):
        """Return directory where files required for processes can be held. Is not clear what this will
        be used for, but it should at least serve as a possibility for the future.

        :param kwargs: ``create`` := If ``True`` assure the  directory exists after the call is done.
        :param tool: tool/plug-in for which the information is returned. If None, then the directory
                     where all information for all tools reside is returned insted (normally, that would
                     be the parent directrory).
        :type tool: str
        :returns: path to the directory."""
        return self._getUserDir("processes", tool, **kwargs)

    def getUserOutputDir(self, tool=None, **kwargs):
        """Return directory where output data for this user is stored.

        :param kwargs: ``create`` := If ``True`` assure the  directory exists after the call is done.
        :param tool: tool/plug-in for which the information is returned. If None, then the directory
                     where all information for all tools reside is returned insted (normally, that would
                     be the parent directrory).
        :type tool: str
        :returns: path to the directory."""
        return self._getUserDir("output", tool, **kwargs)

    def getUserPlotsDir(self, tool=None, **kwargs):
        """Return directory where all plots for this user are stored.

        :param kwargs: ``create`` := If ``True`` assure the  directory exists after the call is done.
        :param tool: tool/plug-in for which the information is returned. If None, then the directory
                     where all information for all tools reside is returned insted (normally, that would
                     be the parent directrory).
        :type tool: str
        :returns: path to the directory."""
        return self._getUserDir("plots", tool, **kwargs)

    def prepareDir(self):
        """Prepares the configuration directory for this user if it's not already been done."""
        if os.path.isdir(self.getUserBaseDir()):
            # we assume preparation was successful... but we might to be sure though...
            # return
            pass

        if not os.path.isdir(self.getUserHome()):
            raise Exception(
                "Can't create configuration, user HOME doesn't exist (%s)"
                % self.getUserHome()
            )

        # create directory for the framework
        # create all required subdirectories
        dir_creators = [
            self.getUserBaseDir,
            self.getUserConfigDir,
            self.getUserCacheDir,
            self.getUserOutputDir,
            self.getUserPlotsDir,
            self.getUserSchedulerInputDir,
            self.getUserSchedulerOutputDir,
        ]

        for f in dir_creators:
            f(create=True)
