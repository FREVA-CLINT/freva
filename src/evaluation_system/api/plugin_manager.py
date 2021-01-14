"""
.. moduleauthor:: Sebastian Illing / estani

This module manages the loading and access to all plug-ins. It is designed as a central registration thorugh
which plug-ins can be accessed.

Plug-ins are automatically registered if  found either in a specific directory ``<evaluation_system_root_dir>/tools``
or by using the environmental variable ``EVALUATION_SYSTEM_PLUGINS``.
This variable must to point to the modules implementing :class:`evaluation_system.api.plugin.PluginAbstract`.

The value stored there is a colon (':') separated list of ``path,package`` comma (',') separated pairs. The path
denotes where the source is to be found, and the package the module name in which the PluginAbstract interface is being
implemented. For example::

    EVALUATION_SYSTEM_PLUGINS=/path/to/some/dir/,something.else.myplugin:/other/different/path,some.plugin:/tmp/test,some.other.plugin
"""

# Initialize the plugin
import os
import sys
import random
import string
import re
import datetime
import shutil
import logging
import json
import imp
import subprocess as sub
from evaluation_system.model.history.models import History, HistoryTag, Configuration
from evaluation_system.model.plugins.models import Parameter
from evaluation_system.api.parameters import ParameterNotFoundError

from evaluation_system.model.repository import getVersion
from evaluation_system.model.user import User
from evaluation_system.misc import config, utils, py27
from subprocess import Popen, STDOUT, PIPE
from multiprocessing import Pool
log = logging.getLogger(__name__)


class PluginManagerException(Exception):
    """For all problems generating while using the plugin manager."""
    pass


PLUGIN_ENV = 'EVALUATION_SYSTEM_PLUGINS'
"""Defines the environmental variable name for pointing to the plug-ins"""

# all plugins modules will be dynamically loaded here.
# __plugin_modules__ = py27.OrderedDict() # we use a ordered dict.
# This allows to override plugins
__plugin_modules_user__ = {}
"""Dictionary of modules holding the plug-ins."""
# __plugins__ = {}
__plugins_user__ = {}
"""Dictionary of plug-ins class_name=>class"""
# __plugins_meta = {}
__plugins_meta_user = {}
"""Dictionary of plug-ins with more information
plugin_name=>{
    name=>plugin_name,
    plugin_class=>class,
    version=>(0,0,0)
    description=>"string"}"""


""" A dictionary which acts as a cache for the git information to
    reduce hard disk access"""
__version_cache = {}


def munge(seq):
    """Generator to remove duplicates from a list without changing it's order.
It's used to keep sys.path tidy.

:param seq: any sequence
:returns: a generator returning the same objects in the same sequence but skipping duplicates."""
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            yield item


def reloadPlugins(user_name=None):
    """Reload all plug-ins. Plug-ins are then loaded first from the :class:`PLUGIN_ENV` environmental
variable and then from the configuration file. This means that the environmental variable has precedence
and can therefore overwrite existing plug-ins (useful for debugging and testing)."""
    if not user_name:
        user_name = User().getName()
    # reset all current plugins
#     for item in __plugins_meta.keys():
#         __plugins_meta.pop(item)
#     for item in __plugin_modules__.keys():
#         __plugin_modules__.pop(item)
#     for item in __plugins__.keys():
#         __plugins__.pop(item)
    __plugin_modules__ = py27.OrderedDict()  # we use a ordered dict. This allows to override plugins
    __plugins__ = {}
    __plugins_meta = {}
    __plugin_modules_user__[user_name] = py27.OrderedDict()
    __plugins_user__[user_name] = py27.OrderedDict()
    __plugins_meta_user[user_name] = py27.OrderedDict()

    extra_plugins = list()
    if PLUGIN_ENV in os.environ:
        # now get all modules loaded from the environment
        for path, module_name in map(lambda item: tuple([e.strip() for e in item.split(',')]),
                                     os.environ[PLUGIN_ENV].split(':')):
            # extend path to be exact by resolving all "user shortcuts" (e.g. '~' or '$HOME')
            path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
            if os.path.isdir(path):
                # we have a plugin_imp with defined api
                sys.path.append(path)
                # TODO this is not working like in the previous loop. Though we might just want to remove it,
                # as there seem to be no use for this info...
                __plugin_modules__[module_name] = os.path.join(path, module_name)
                extra_plugins.append(module_name)
            else:
                log.warn("Cannot load %s, directory missing: %s", module_name, path)

    # the same for user specific env variable
    if user_name:
        if PLUGIN_ENV+'_'+user_name in os.environ:
            # now get all modules loaded from the environment
            for path, module_name in map(lambda item: tuple([e.strip() for e in item.split(',')]),
                                         os.environ[PLUGIN_ENV+'_'+user_name].split(':')):
                # extend path to be exact by resolving all "user shortcuts" (e.g. '~' or '$HOME')
                path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
                if os.path.isdir(path):
                    # we have a plugin_imp with defined api
                    sys.path.append(path)
                    # TODO this is not working like in the previous loop. Though we might just want to remove it,
                    # as there seem to be no use for this info...
                    __plugin_modules__[module_name] = os.path.join(path, module_name)
                    extra_plugins.append(module_name)
                else:
                    log.warn("Cannot load %s, directory missing: %s", module_name, path)

    # get the tools directory from the current one
    # get all modules from the tool directory
    plugins = list(config.get(config.PLUGINS))
    for plugin_name in plugins:
        py_dir = config.get_plugin(plugin_name, config.PLUGIN_PYTHON_PATH)
        py_mod = config.get_plugin(plugin_name, config.PLUGIN_MODULE)
        if os.path.isdir(py_dir):
            if py_mod in __plugin_modules__:
                file_path = __plugin_modules__[py_mod]+'.py'
                log.warn("Module '%s' is test being overwritten by: %s", py_mod, file_path)
            else:
                log.debug("Loading '%s'", plugin_name)
                sys.path.append(py_dir)
                __plugin_modules__[plugin_name] = os.path.join(py_dir, py_mod)
        else:
            log.warn("Cannot load '%s' directory missing: %s", plugin_name, py_dir)

    # new way of loading plugins
    import re
    reg = re.compile(r'__short_description__\s*=(.*)')
    r = re.compile(r'\'(.*)\'')
    r_2 = re.compile(r'\"(.*)\"')
    r_list = re.compile(r'\[(.*)\]')
    reg_class_name = re.compile(r'class\s*(.*)')
    # reg for categories
    cat_reg = re.compile(r'__category__\s*=(.*)')
    # reg for tags
    tag_reg = re.compile(r'__tags__\s*=(.*)')
    for plugin_name, plugin_mod in __plugin_modules__.items():
        f = open(plugin_mod+'.py', 'r')
        description = None
        class_name = None
        category = None
        tags = None

        class_name_str = ''
        for line in f:
            description = re.search(reg, line)
            if description is not None:
                description_str = re.search(r, description.groups()[0])
                if description_str is None:
                    description_str = re.search(r_2, description.groups()[0])
                if description_str is not None:
                    description_str = description_str.groups()[0]
            # search for category
            category_search = re.search(cat_reg, line)
            if category_search:
                category = re.search(r, category_search.groups()[0])
                category = category.groups()[0]
            # search for tags
            tags_search = re.search(tag_reg, line)
            if tags_search:
                tags = re.search(r_list, tags_search.groups()[0])
                tags = list(eval(tags.groups()[0]))

            # search for classname
            class_name = re.search(reg_class_name, line)
            if class_name is not None:
                # TODO: Maybe this is not robust enough.
                # What if class inherits from other Base Class?
                if 'PluginAbstract' in class_name.groups()[0]:
                    class_name_str = re.sub(r'\(.*', '', class_name.groups()[0])
        if class_name_str != ''  and class_name_str.lower() not in __plugins_meta.keys():
            __plugins_meta[class_name_str.lower()] = dict(name=class_name_str,
                                                          plugin_class=class_name_str,
                                                          plugin_module=plugin_mod,
                                                          description=description_str,
                                                          user_exported=plugin_name in extra_plugins,
                                                          category=category,
                                                          tags=tags)
            __plugins__[class_name_str] = class_name_str
        elif class_name_str != '':
            log.warn("Default plugin %s is being overwritten by: %s",
                     class_name_str, __plugins_meta[class_name_str.lower()]['plugin_module']+'.py')
    sys.path = [p for p in munge(sys.path)]

    __plugin_modules_user__[user_name] = __plugin_modules__
    __plugins_user__[user_name] = __plugins__
    __plugins_meta_user[user_name] = __plugins_meta


# This only runs once after start. To load new plugins on the fly we have 2 possibilities
# 1) Watch the tool directory
# 2) Use the plugin metaclass trigger (see `evaluation_system.api.plugin`
reloadPlugins()


def get_plugins_user():
    return __plugins_meta_user


def getPlugins(user_name=User().getName()):
    """Return a dictionary of plug-ins holding the plug-in classes and meta-data about them.
It's a dictionary with the ``plugin_name`` in lower case of what :class:`getPluginDict` returns.

The dictionary is therefore defined as::

    {plugin_name.lower() : dict(name = plugin_name,
                                plugin_class = plugin_class,
                                version=plugin_class.__version__,
                                description=plugin_class.__short_description__)

This can be used if the plug-in name is unknown."""
    return __plugins_meta_user[user_name]


def getPluginDict(plugin_name, user_name=User().getName()):
    """Return the requested plug-in dictionary entry or raise an exception if not found.

name
    The class name implementing the plugin (and therefore inheriting from
    :class:`evaluation_system.api.plugin.PluginAbstract`)
plugin_class
    The class itself.
version
    A 3-value tuple representing the plug-in version (major, minor, build)
description
    A string providing a hort description about what the plugin does.

:type plugin_name: str
:param plugin_name: Name of the plug-in to search for.
:return: a dictionary with information on the plug-in
"""
    plugin_name = plugin_name.lower()
    if plugin_name not in getPlugins(user_name).keys():
        reloadPlugins(user_name)
        if plugin_name not in getPlugins(user_name).keys():
            mesg = "No plugin named: %s" % plugin_name
            similar_words = utils.find_similar_words(plugin_name, getPlugins(user_name))
            if similar_words:
                mesg = "%s\n Did you mean this?\n\t%s" % (mesg, '\n\t'.join(similar_words))
            mesg = '%s\n\nUse --list-tools to list all available plug-ins.' % mesg
            raise PluginManagerException(mesg + ' %s' % user_name)

    return getPlugins(user_name)[plugin_name]


def getPluginInstance(plugin_name, user=None, user_name=User().getName()):
    """Return an instance of the requested plug-in or raise an exception if not found.
At the current time we are just creating new instances, but this might change in the future, so it's
*not* guaranteed that the instances are *unique*, i.e. they might be re-used and/or shared.

:type plugin_name: str
:param plugin_name: Name of the plugin to search for.
:type user: :class:`evaluation_system.model.user.User`s_meta

:param user: User for which this plug-in instance is to be acquired. If not given the user running this program
will be used.
:return: an instance of the plug-in. Might not be unique."""
    # in case we want to cache the creation of the plugin classes.
    if user is None:
        user = User()
    plugin_dict = getPluginDict(plugin_name, user_name)
    plugin_module = imp.load_source('%s' % plugin_dict['plugin_class'], plugin_dict['plugin_module']+'.py')
    return getattr(plugin_module, plugin_dict['plugin_class'])(user=user)


def parseArguments(plugin_name, arguments, use_user_defaults=False, user=None, config_file=None, check_errors=True):
    """Manages the parsing of arguments which are passed as a list of strings. These are in turn
sent to an instance of the plugin, that will handle the parsing. This is why the user is required
to be known at this stage.

:type plugin_name: str
:param plugin_name: Name of the plugin to search for.
:type arguments: list of strings
:param arguments: it will be parsed by the plug-in (see :class:`evaluation_system.api.plugin.parseArguments`)
:type use_user_defaults: bool
:param use_user_defaults: If ``True`` and a user configuration is found, this will be used as a default for all non
set arguments. So the value will be determined according to the first found instance of: argument,
user default, tool default
:type user: :class:`evaluation_system.model.user.User`
:param user: The user for whom this arguments are parsed.
:type config_file: str
:param config_file: path to a file from where the setup will read a configuration. If None, the default
 user dependent one will be used. This will be completely skipped if ``use_user_defaults`` is ``False``.
:return: A dictionary with the parsed configuration."""
    plugin_name = plugin_name.lower()
    if user is None:
        user = User()

    p = getPluginInstance(plugin_name, user)
    complete_conf = p.__parameters__.parseArguments(arguments, use_defaults=True, check_errors=False)

    # if we are using user defaults then load them first
    if use_user_defaults:
        user_config_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(user_config_file):
            with open(user_config_file, 'r') as f:
                complete_conf.update(p.readConfiguration(f))
    # now if we still have a config file update what the configuration with it

    if isinstance(config_file, str):
        if config_file == '-':
            # reading from stdin
            complete_conf.update(p.readConfiguration(sys.stdin))

        elif config_file is not None:
            with open(config_file, 'r') as f:
                complete_conf.update(p.readConfiguration(f))
    elif config_file is not None:
        # if it's not a string and is something, we assume is something that can be read from
        complete_conf.update(p.readConfiguration(config_file))

    # update with user defaults if desired
    complete_conf.update(p.__parameters__.parseArguments(arguments, check_errors=False))
    # we haven't check for errors because we might have a half implemented configuration
    # some required field might have already been setup (user/system defaults, files, etc)
    # but better if we check them
    if check_errors:
        p.__parameters__.validate_errors(complete_conf, raise_exception=True)

    return complete_conf


def writeSetup(plugin_name, config_dict=None, user=None, config_file=None):
    """Writes the plug-in setup to disk. This is the configuration for the plug-in itself and not that
of the tool (which is what normally the plug-in encapsulates). The plug-in is not required to write anything to
disk when running the tool; it might instead configure it from the command line, environmental variables or
any other method.

:type plugin_name: str
:param plugin_name: name of the referred plugin.
:type config_dict: dict or metadict
:param config_dict: The configuration being stored. If is None, the default configuration will be stored,
    this might be incomplete.
:type user: :class:`evaluation_system.model.user.User`
:param user: The user for whom this arguments are parsed.
:type config_file: str
:param config_file: path to a file  where the setup will be stored. If None, the default user dependent one will be
used. This will be completely skipped if ``use_user_defaults`` is ``False``.
:returns: The path to the configuration file that was written."""
    plugin_name = plugin_name.lower()
    if user is None:
        user = User()
    p = getPluginInstance(plugin_name, user, user.getName())
    complete_conf = p.setupConfiguration(config_dict=config_dict, check_cfg=False, substitute=False)

    if config_file is None:
        # make sure the required directory structure and data is in place
        user.prepareDir()

        config_file = user.getUserToolConfig(plugin_name, create=True)

    if config_file == '-':
        p.saveConfiguration(sys.stdout, config_dict=complete_conf)
    else:
        with open(config_file, 'w') as f:
            p.saveConfiguration(f, config_dict=complete_conf)

    return config_file


def _preview_copy(source_path, dest_path):
    """
    Copy images for preview
    :type source_path: str
    :param source_path: the source
    :type dest_path: str
    :param dest_path: the destination
    """
    # previously used
    # shutil.copyfile(source_path, dest_path)
    # a not very pythonic work-around
    if source_path.split('.')[-1] in ['pdf', 'zip']:  # don't resize pdf files
        shutil.copyfile(source_path, dest_path)
    else:
        command = ['convert', '-resize', '800x>', source_path, dest_path]
        sub.call(command)
    os.chmod(dest_path, 509)

def _preview_convert(source_path, dest_path):
    """
    Converts images
    :type source_path: str
    :param source_path: the file name of the file to convert
    :type dest_path: str
    :param dest_path: The file name of the converted file
    """

    # a not very pythonic work-around
    command = ['convert', '-resize', '800x', source_path, dest_path]
    sub.call(command)
    # we need this on mistral, becuase otherwise apache can't read the files
    # TODO: Why was is working on MiKlip?
    os.chmod(dest_path, 509)

    # The following is preferable when supported by the installed PIT version
    # im = Image.open(source_path)
    # im.save(dest_path)


def _preview_generate_name(plugin_name, file_name, metadata):
    """
    Creates a filename  according to the plugin_name, timestamp and
    an eight character random string
    :type plugin_name: str
    :param plugin_name: name of the referred plugin.
    :type file_name: str
    :param file_name: the file to create a preview name for
    :type ext: str
    :param ext: the extension of the file to be created
    :type metadata: dict
    :param metadata: the meta-data for the file, to access timestamp
    """
    random_suffix = ''.join(random.choice(string.ascii_letters) for i in range(8))

    ctime = metadata.get('timestamp', '')

    if ctime:
        time_string = datetime.datetime.fromtimestamp(ctime).strftime('%Y%m%d_%H%M%S')
        ctime = '%s_' % time_string

    return plugin_name + '_' + ctime + random_suffix


def _preview_unique_file(plugin_name, file_name, ext, metadata):
    """
    This routine creates a unique filename for the preview
    :type plugin_name: str
    :param plugin_name: name of the referred plugin.
    :type file_name: str
    :param file_name: the file to create a preview name for
    :type ext: str
    :param ext: the extension of the file to be created
    :type metadata: dict
    :param metadata: the meta-data for the file, to access timestamp
    """
    path = config.get(config.PREVIEW_PATH)
    subdir = datetime.datetime.now().strftime('%Y%m%d')
    name = _preview_generate_name(plugin_name, file_name, metadata)
    name += ext
    full_path = os.path.join(path, subdir)
    full_name = os.path.join(full_path, name)

    if path.strip() and not os.path.isdir(full_path):
        utils.supermakedirs(full_path, 0o0777)

    if os.path.isfile(full_name):
        return _preview_unique_file(plugin_name, file_name, ext, metadata)

    return full_name


def _preview_create(plugin_name, result):
    """
    This routine creates the preview. And adds the created files
    to the result dictionary.
    :type plugin_name: str
    :param plugin_name: name of the referred plugin.
    :type result: meta_dict
    :param result: a meta dictionary describing the result files
    """

    todo_list = []
    result_list = []
    for file_name in result:
        metadata = result[file_name]
        todo = metadata.get('todo', '')

        if todo == 'copy':
            ext = os.path.splitext(file_name)[-1]
            target_name = _preview_unique_file(plugin_name, file_name, ext, metadata)
            todo_list.append((_preview_copy, file_name, target_name))
            metadata['preview_path'] = target_name
            result_list.append(target_name)
        elif todo == 'convert':
            target_name = _preview_unique_file(plugin_name, file_name, '.png', metadata)
            todo_list.append((_preview_convert, file_name, target_name))
            metadata['preview_path'] = target_name
            result_list.append(target_name)
        result[file_name] = metadata

    preview_path = config.get(config.PREVIEW_PATH)

    if preview_path.strip() and todo_list:
        p = Pool(config.NUMBER_OF_PROCESSES)
        p.map(utils.mp_wrap_fn, todo_list)
    return result_list


def generateCaption(caption, toolname):
    """
    Generates a standardized caption including the toolname.
    :type caption: str
    :param caption: The caption to be standardized
    :type toolname: str
    :param toolname: the toolname
    :return: String containing the standardized caption
    """
    import re

    caption = caption.strip()
    toolname = toolname.strip().upper()

    retval = toolname

    if caption.lower() != toolname.lower():
        pattern = r"^\*"
        if re.search(pattern, caption, re.IGNORECASE):
            caption = caption[1:]

        pattern = r'\(' + toolname + r'\)$'
        if re.search(pattern, caption, re.IGNORECASE) is None:
            retval = caption + ' (' + toolname + ')'
        else:
            retval = caption
    else:
        # this assures that the toolname appears in the user preferred case
        retval = caption

    return retval


def runTool(plugin_name, config_dict=None, user=None, scheduled_id=None,
            caption=None, unique_output=True):
    """Runs a tool and stores this "run" in the :class:`evaluation_system.model.db.UserDB`.

:type plugin_name: str
:param plugin_name: name of the referred plugin.
:type config_dict: dict or metadict
:param config_dict: The configuration used for running the tool. If is None, the default configuration will be stored,
    this might be incomplete.
:type user: :class:`evaluation_system.model.user.User`
:param user: The user starting the tool
:type scheduled_id: int
:param scheduled_id: if the process is already scheduled then put the row id here
:type caption: str
:param caption: the caption to set.
"""

    plugin_name = plugin_name.lower()
    if user is None:
        user = User()

    p = getPluginInstance(plugin_name, user)
    complete_conf = None

    # check whether a scheduled id is given
    if scheduled_id:
        config_dict = loadScheduledConf(plugin_name, scheduled_id, user)
    if config_dict is None:
        conf_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(conf_file):
            log.debug('Loading config file %s', conf_file)
            with open(conf_file, 'r') as f:
                complete_conf = p.readConfiguration(f)
        else:
            log.debug('No config file was found in %s', conf_file)
    if complete_conf is None:
        # at this stage we want to resolve or tokens and perform some kind of sanity check before going further
        complete_conf = p.setupConfiguration(config_dict=config_dict, recursion=True)

    log.debug('Running %s with %s', plugin_name, complete_conf)

    rowid = 0

    if scheduled_id:
        user.getUserDB().upgradeStatus(scheduled_id,
                                       user.getName(),
                                       History.processStatus.running)
        rowid = scheduled_id
    elif user:
        version_details = getVersion(plugin_name)
        rowid = user.getUserDB().storeHistory(p,
                                              complete_conf,
                                              user.getName(),
                                              History.processStatus.running,
                                              version_details=version_details,
                                              caption=caption)

        # follow the notes
        followHistoryTag(rowid, user.getName(), 'Owner')

    try:
        # we want that the rowid is visible to the tool
        p.rowid = rowid
        # In any case we have now a complete setup in complete_conf
        result = p._runTool(config_dict=complete_conf,
                            unique_output=unique_output)

        # save results when existing
        if result is None:
            user.getUserDB().upgradeStatus(rowid,
                                           user.getName(),
                                           History.processStatus.finished_no_output)

        else:
            # create the preview
            preview_path = config.get(config.PREVIEW_PATH, None)

            if preview_path:
                logging.debug('Converting....')
                _preview_create(plugin_name, result)
                logging.debug('finished')

            # write the created files to the database
            logging.debug('Storing results into data base....')
            user.getUserDB().storeResults(rowid, result)
            logging.debug('finished')

            # temporary set all processes to finished
            user.getUserDB().upgradeStatus(rowid,
                                           user.getName(),
                                           History.processStatus.finished)
    except:
        user.getUserDB().upgradeStatus(rowid,
                                       user.getName(),
                                       History.processStatus.broken)

        raise

    return result


def scheduleTool(plugin_name, slurmoutdir=None, config_dict=None, user=None,
                 caption=None, unique_output=True):
    """Schedules  a tool and stores this "run" in the :class:`evaluation_system.model.db.UserDB`.

:type plugin_name: str
:param plugin_name: name of the referred plugin.
:type slurmoutdir: string
:param slurmoutdir: directory for the output
:type config_dict: dict or metadict
:param config_dict: The configuration used for running the tool. If is None, the default configuration will be stored,
    this might be incomplete.
:type user: :class:`evaluation_system.model.user.User`
:param user: The user starting the tool
:type scheduled_id: int
:param scheduled_id: if the process is already scheduled then put the row id here
:type caption: str
:param caption: the caption to set.
"""

    plugin_name = plugin_name.lower()
    if user is None:
        user = User()

    p = getPluginInstance(plugin_name, user)
    complete_conf = None

    # check whether a scheduled id is given
    if config_dict is None:
        conf_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(conf_file):
            log.debug('Loading config file %s', conf_file)
            with open(conf_file, 'r') as f:
                complete_conf = p.readConfiguration(f)
        else:
            log.debug('No config file was found in %s', conf_file)
    if complete_conf is None:
        # at this stage we want to resolve or tokens and perform some kind of sanity check before going further
        complete_conf = p.setupConfiguration(config_dict=config_dict, recursion=True)

    log.debug('Schedule %s with %s', plugin_name, complete_conf)

    slurmindir = os.path.join(user.getUserSchedulerInputDir(), user.getName())
    if not os.path.exists(slurmindir):
        utils.supermakedirs(slurmindir, 0o0777)

    version_details = getVersion(plugin_name)
    rowid = user.getUserDB().storeHistory(p,
                                          complete_conf,
                                          user.getName(),
                                          History.processStatus.not_scheduled,
                                          version_details=version_details,
                                          caption=caption)

    # follow the notes
    followHistoryTag(rowid, user.getName(), 'Owner')

    # set the SLURM output directory
    if not slurmoutdir:
        slurmoutdir = user.getUserSchedulerOutputDir()
        slurmoutdir = os.path.join(slurmoutdir, plugin_name)

    if not os.path.exists(slurmoutdir):
        utils.supermakedirs(slurmoutdir, 0o0777)

    # write the SLURM file
    p.rowid = rowid
    full_path = os.path.join(slurmindir, p.suggestSlurmFileName())
    with open(full_path, 'w') as fp:
        p.writeSlurmFile(fp,
                         scheduled_id=rowid,
                         user=user,
                         slurmoutdir=slurmoutdir,
                         unique_output=unique_output)

    # create the batch command
    command = ['/bin/bash',
               '-c',
               '%s %s %s\n' % (config.get('scheduler_command'),  # SCHEDULER_COMMAND,
                                        config.SCHEDULER_OPTIONS,
                                        #user.getName(),
                                        full_path)]

    # run this
    logging.debug("Command: " + str(command))
    p = Popen(command, stdout=PIPE, stderr=STDOUT)
    (stdout, stderr) = p.communicate()

    logging.debug("scheduler call output:\n" + str(stdout))
    logging.debug("scheduler call error:\n" + str(stderr))

    # get the very first line only
    out_first_line = stdout.split('\n')[0]

    # read the id from stdout
    if out_first_line.split(' ')[0] == 'Submitted':
        slurm_id = int(out_first_line.split(' ')[-1])
    else:
        slurm_id = 0
        raise Exception('Unexpected scheduler output:\n%s' % out_first_line)

    slurm_out = os.path.join(slurmoutdir,
                             'slurm-%i.out' % slurm_id)

    # create a standard slurm file to view with less
    with open(slurm_out, 'w') as the_file:
        the_file.write('Certainly, your job is pending with id %i.\n' % slurm_id)
        the_file.write('You can get further information using the command squeue.\n')
        the_file.write('\nThis file was automatically created by the evaluation system.\n')
        the_file.write('It will be overwritten by the output of %s.\n' % plugin_name)

    # set the slurm output file
    user.getUserDB().scheduleEntry(rowid, user.getName(), slurm_out)

    return rowid, slurm_out


def getHistory(plugin_name=None, limit=-1, since=None, until=None, entry_ids=None, user=None):
    """Returns the history from the given user.
This is just a wrapper for the defined db interface accessed via the user object.
See :class:`evaluation_system.model.db.UserDB.getHistory` for more information on this interface."""
    if plugin_name is not None:
        plugin_name = plugin_name.lower()
    if user is None:
        user = User()

    return user.getUserDB().getHistory(plugin_name, limit, since=since, until=until,
                                       entry_ids=entry_ids, uid = user.getName())


# def getResults(history_id, filetype=None, user=None):
#     """ Returns the results for a given history id
# This is a wrapper for the function defined in db.py, like getHistory. """
#     if user is None:
#         user = User()
#
#     return user.getUserDB().getResults(history_id, filetype)


def getCommandString(entry_id, user=None, command_name='freva', command_options='--plugin'):
    """
    Return the parameter string of a history entry.
    :type entry_id: integer
    :param entry_id: the history id
    :type user: User
    :param user: A user to access the database
    """
    if user is None:
        user = User()

    h = user.getUserDB().getHistory(entry_ids=int(entry_id))

    return getCommandStringFromRow(h[0], command_name, command_options)


def getCommandStringFromRow(history_row, command_name='analyze', command_options='--tool'):
    """
    Return the parameter string of a history entry.
    :type history_row: row
    :param history_row: row of the history table
    """

    result = "%s %s %s" % (command_name, command_options, history_row.tool)

    configuration = history_row.config_dict()

    # find lists
    re_list_pattern = r"^\[.*\]$"
    re_list = re.compile(re_list_pattern)

    for k in configuration.keys():
        value = configuration[k]

        if value is not None:
            # convert non-None values to string
            value = str(value)

            # remove brackets from list
            if re_list.match(value):
                value = value[1:-1]

            result = "%s %s='%s'" % (result, str(k), value)

    return result


def loadScheduledConf(plugin_name, entry_id, user):
    """
    This routine loads the configuration from a scheduled plug-in
    """
    h = getHistory(plugin_name=plugin_name, entry_ids=entry_id, user=user)
    # only one row should be selected
    row = h[0]

    # scheduled jobs only
    if row.status != History.processStatus.scheduled:
        raise Exception("This is not a scheduled job (status %i)!" % row.status)

    return row.config_dict()


def getConfigName(pluginname):
    """
    Returns the name of a tool as written in the configuration file.
    This is especially useful when accessing the configuration.
    """
    from inspect import getmodule

    try:
        plugin = getPluginInstance(pluginname.lower())

        modulename = getmodule(plugin)

        for name, module in __plugin_modules__[User().getName()].items():
            if modulename == getmodule(module):
                return name

    except Exception as e:
        log.debug('[getConfigName] ' + str(e))

    return None


def getErrorWarning(tool_name):
    """
    returns a tuple (Error, Warning) with an error message or a warning
    read from the config file
    """
    plugin_name = getConfigName(tool_name)

    error_file = ''
    error_message = ''

    warning_file = ''
    warning_message = ''

    try:
        error_file = config.get_plugin(plugin_name, "error_file", '')
        error_message = config.get_plugin(plugin_name, "error_message", '')

        warning_file = config.get_plugin(plugin_name, "warning_file", '')
        warning_message = config.get_plugin(plugin_name, "warning_message", '')
    except Exception as e:
        log.debug(str(e))

    if error_file:
        try:
            f = open(error_file, 'r')
            error_message = f.read()
            f.close()
        except Exception as e:
            if not error_message:
                log.warn('Could not read error description\n%s' % str(e))
                error_message = ''

    if warning_file:
        try:
            f = open(warning_file, 'r')
            warning_message = f.read()
            f.close()
        except Exception as e:
            if not warning_message:
                log.warn('Could not read warning\n%s' % str(e))
                warning_message = ''

    error_message = error_message.strip()
    warning_message = warning_message.strip()

    return error_message, warning_message


def followHistoryTag(history_id, user_name, info=''):
    """
    Adds the history tag follow
    """
    tagType = HistoryTag.tagType.follow
    rows = HistoryTag.objects.filter(history_id_id=history_id,
                                     type=tagType,
                                     uid_id=user_name)
    if len(rows) == 0:
        user = User(user_name)
        user.getUserDB().addHistoryTag(history_id, tagType, info, uid=user_name)


def unfollowHistoryTag(history_id, user_name):
    """
    Update all follow history tags to unfollow for the specified
    history entry and user
    """
    tagType = HistoryTag.tagType.follow
    rows = HistoryTag.objects.filter(history_id_id=history_id,
                                     type = tagType,
                                     uid_id = user_name)

    user = User(user_name)
    for row in rows:
        user.getUserDB().updateHistoryTag(row.id,
                                          HistoryTag.tagType.unfollow,
                                          uid=user_name)


def getPluginVersion(pluginname):
    import evaluation_system.model.repository as repository

    from inspect import getfile, currentframe

    version = __version_cache.get(pluginname, None)

    if version is None:

        plugin = getPlugins().get(pluginname, None)

        srcfile = ''

        if plugin is not None:
            srcfile = plugin['plugin_module']
        elif pluginname == 'self':
            srcfile = getfile(currentframe())
        else:
            mesg = 'Plugin <%s> not found' % pluginname
            raise PluginManagerException(mesg)

        version = repository.getVersion(srcfile)
        __version_cache[pluginname] = version

    return version


def getVersion(pluginname):
    """
    returns the internal version of a tool (index in datatable)
    if the version is not indexed it will be created
    """
    tool_name = pluginname.lower()
    p = getPluginInstance(pluginname)
    version = repr(p.__version__)
    (repos_tool, version_tool) = getPluginVersion(pluginname)
    (repos_api, version_api) = getPluginVersion('self')

    version_id = User().getUserDB().getVersionId(tool_name,
                                                 version,
                                                 repos_api,
                                                 version_api,
                                                 repos_tool,
                                                 version_tool)

    if version_id is None:
        version_id = User().getUserDB().newVersion(tool_name,
                                                   version,
                                                   repos_api,
                                                   version_api,
                                                   repos_tool,
                                                   version_tool)

    return version_id


def dict2conf(toolname, conf_dict, user_name=User().getName()):
    """
    :param conf_dict: dictionary with configuration to look up
    :type conf_dict: dict

    This routine returns a list of configuration model objects.
    A useful routine to get similar results.
    """

    conf = []

    paramstring = []

    tool = getPluginInstance(toolname, user_name=user_name)

    for key, value in conf_dict.items():
        o = Parameter.objects.filter(tool=toolname, parameter_name=key).order_by('-id')

        if len(o) == 0:
            string = 'Parameter <%s> not found' % key
            raise ParameterNotFoundError(string)

        else:
            paramstring = ['%s=%s' % (key, str(value))]
            realvalue = tool.__parameters__.parseArguments(paramstring, check_errors=False)[key]
            conf_object = Configuration()
            conf_object.parameter_id_id = o[0].id
            conf_object.value = json.dumps(realvalue)
            conf.append(conf_object)

    return conf
