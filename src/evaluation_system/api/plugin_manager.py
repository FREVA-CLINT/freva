'''
.. moduleauthor:: estani <estanislao.gonzalez@met.fu-berlin.de>

This module manages the loading and access to all plug-ins. It is designed as a central registration thorugh
which plug-ins can be accessed.

Plug-ins are automatically registered if  found either in a specific directory ``<evaluation_system_root_dir>/tools``
or by using the environmental variable ``EVALUATION_SYSTEM_PLUGINS``.
This variable must to point to the modules implementing :class:`evaluation_system.api.plugin.PluginAbstract`. 

The value stored there is a colon (':') separated list of ``path,package`` comma (',') separated pairs. The path
denotes where the source is to be found, and the package the module name in which the PluginAbstract interface is being implemented. For example::

    EVALUATION_SYSTEM_PLUGINS=/path/to/some/dir/,something.else.myplugin:/other/different/path,some.plugin:/tmp/test,some.other.plugin

'''


#*** Initialize the plugin
import os
import sys
import random
import string
import re
import datetime
import shutil
import logging
import subprocess as sub
#from PIL import Image
log = logging.getLogger(__name__)

import evaluation_system.api.plugin as plugin
import evaluation_system.model.db as db
from evaluation_system.model.user import User
from evaluation_system.misc import config, utils
from subprocess import Popen, STDOUT, PIPE
from multiprocessing import Pool

class PluginManagerException(Exception):
    """For all problems generating while using the plugin manager."""
    pass


PLUGIN_ENV = 'EVALUATION_SYSTEM_PLUGINS'
"""Defines the environmental variable name for pointing to the plug-ins"""
    
#all plugins modules will be dynamically loaded here.
__plugin_modules__ = {}
"""Dictionary of modules holding the plug-ins."""
__plugins__ = {}
"""Dictionary of plug-ins class_name=>class"""
__plugins_meta = {}
"""Dictionary of plug-ins with more information 
plugin_name=>{
    name=>plugin_name,
    plugin_class=>class,
    version=>(0,0,0)
    description=>"string"}"""

 
def munge( seq ):
    """Generator to remove duplicates from a list without changing it's order.
It's used to keep sys.path tidy.

:param seq: any sequence
:returns: a generator returning the same objects in the same sequence but skipping duplicates."""
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add( item )
            yield item
            
def reloadPlugins():
    """Reload all plug-ins. Plug-ins are then loaded first from the :class:`PLUGIN_ENV` environmental
variable and then from the configuration file. This means that the environmental variable has precedence
and can therefore overwrite existing plug-ins (useful for debugging and testing)."""
    #extra_modules = [(path, module) ... ]
    if PLUGIN_ENV in os.environ:
        #now get all modules loaded from the environment
        for path, module_name in map( lambda item: tuple([e.strip() for e in item.split(',')]), 
                                 os.environ[PLUGIN_ENV].split(':')):                
            #extend path to be exact by resolving all "user shortcuts" (e.g. '~' or '$HOME')
            path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
            if os.path.isdir(path):
                #we have a plugin_imp with defined api
                sys.path.append(path)
                #TODO this is not working like in the previous loop. Though we might just want to remove it,
                #as there seem to be no use for this info...
                try:
                    __plugin_modules__[module_name] = __import__(module_name)
                except ImportError as e:
                    #we handle this as a warning 
                    log.warning("Cannot import module '%s' from %s. (msg: '%s')", module_name, path, e)
            else:
                log.warn("Cannot load %s, directory missing: %s", module_name, path)

    #get the tools directory from the current one
    #get all modules from the tool directory
    plugins = list(config.get(config.PLUGINS))
    for plugin_name in plugins:
        py_dir = config.get_plugin(plugin_name, config.PLUGIN_PYTHON_PATH)
        py_mod = config.get_plugin(plugin_name, config.PLUGIN_MODULE)
        if os.path.isdir(py_dir):
            if py_mod in __plugin_modules__:
                from inspect import getfile
                file_path = getfile(__plugin_modules__[py_mod])
                file_path = os.path.split(file_path)[0]
                log.warn("Module '%s' is test being overwritten by: %s", py_mod, file_path)
            else:
                log.debug("Loading '%s'", plugin_name)
                sys.path.append(py_dir)
                try:
                    __plugin_modules__[plugin_name] = __import__(py_mod)
                except ImportError:
                    #this is an error in this case as is in the central system
                    log.error("Cannot import module '%s' from %s.", py_mod, py_dir)
                    raise
        else:
            log.warn("Cannot load '%s' directory missing: %s", plugin_name, py_dir)

    #no clean that path from duplicates...
    sys.path = [p for p in munge(sys.path)]
    
    #load all plugin classes found (they are loaded when loading the modules)
    for plug_class in plugin.PluginAbstract.__subclasses__():
        if plug_class.__name__ not in __plugins__:
            __plugins__[plug_class.__name__] = plug_class
        else:
            from inspect import getfile
            log.warn("Default plugin %s is being overwritten by: %s", plug_class.__name__, getfile(__plugins__[plug_class.__name__]))

    #now fill up the metadata
    for plugin_name, plugin_class in __plugins__.items():
        __plugins_meta[plugin_name.lower()] = dict(name=plugin_name,
                           plugin_class=plugin_class,
                           version=plugin_class.__version__,
                           description=plugin_class.__short_description__)
#This only runs once after start. To load new plugins on the fly we have 2 possibilities
#1) Watch the tool directory
#2) Use the plugin metaclass trigger (see `evaluation_system.api.plugin`
reloadPlugins()

def getPluginGitVersion(pluginname):
    from inspect import getfile
    plugin = getPlugins().get(pluginname, None)
    
    version = None


    if not plugin is None:
        srcfile = getfile(__plugins__[plugin['plugin_class'].__name__])
        (dirname, filename) = os.path.split(srcfile)
        command = 'module load git > /dev/null 2> /dev/null;'
        if dirname:
            command += 'cd %s 2> /dev/null;' % dirname
        command += 'git show-ref --heads --hash'
        bash = ['/bin/bash',  '-c',  command]
        p = Popen(bash, stdout=PIPE, stderr=STDOUT)
        
        (stdout, stderr) = p.communicate()
        return (stdout, stderr)
    
    

def getPlugins():
    """Return a dictionary of plug-ins holding the plug-in classes and meta-data about them.
It's a dictionary with the ``plugin_name`` in lower case of what :class:`getPluginDict` returns.

The dictionary is therefore defined as::

    {plugin_name.lower() : dict(name = plugin_name,
                                plugin_class = plugin_class,
                                version=plugin_class.__version__,
                                description=plugin_class.__short_description__)

This can be used if the plug-in name is unknown."""
    return __plugins_meta

def getPluginDict(plugin_name):
    """Return the requested plug-in dictionary entry or raise an exception if not found.

name
    The class name implementing the plugin (and therefore inheriting from :class:`evaluation_system.api.plugin.PluginAbstract`)
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
    if plugin_name not in getPlugins():
        mesg = "No plugin named: %s" % plugin_name
        similar_words = utils.find_similar_words(plugin_name, getPlugins())
        if similar_words: mesg = "%s\n Did you mean this?\n\t%s" % (mesg, '\n\t'.join(similar_words))
        mesg = '%s\n\nUse --list-tools to list all available plug-ins.' % mesg
        raise PluginManagerException(mesg)
    
    return getPlugins()[plugin_name]

def getPluginInstance(plugin_name, user = None):
    """Return an instance of the requested plug-in or raise an exception if not found.
At the current time we are just creating new instances, but this might change in the future, so it's
*not* guaranteed that the instances are *unique*, i.e. they might be re-used and/or shared.

:type plugin_name: str
:param plugin_name: Name of the plugin to search for.
:type user: :class:`evaluation_system.model.user.User`
:param user: User for which this plug-in instance is to be acquired. If not given the user running this program will be used.
:return: an instance of the plug-in. Might not be unique."""
    #in case we want to cache the creation of the plugin classes.
    if user is None: user = User()
    return getPluginDict(plugin_name)['plugin_class'](user=user)

def parseArguments(plugin_name, arguments, use_user_defaults=False, user=None, config_file=None, check_errors=True):
    """Manages the parsing of arguments which are passed as a list of strings. These are in turn
sent to an instance of the plugin, that will handle the parsing. This is why the user is required
to be known at this stage.
    
:type plugin_name: str
:param plugin_name: Name of the plugin to search for.
:type arguments: list of strings
:param arguments: it will be parsed by the plug-in (see :class:`evaluation_system.api.plugin.parseArguments`)
:type use_user_defaults: bool
:param use_user_defaults: If ``True`` and a user configuration is found, this will be used as a default for all non set arguments.
                          So the value will be determined according to the first found instance of: argument, user default, tool default
:type user: :class:`evaluation_system.model.user.User`
:param user: The user for whom this arguments are parsed.
:type config_file: str
:param config_file: path to a file from where the setup will read a configuration. If None, the default user dependent one will be used. 
                    This will be completely skipped if ``use_user_defaults`` is ``False``.
:return: A dictionary with the parsed configuration."""
    plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    p = getPluginInstance(plugin_name, user)
    complete_conf = p.__parameters__.parseArguments(arguments, use_defaults=True, check_errors=False)
    
    #if we are using user defaults then load them first
    if use_user_defaults:
        user_config_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(user_config_file):
            with open(user_config_file, 'r') as f:
                complete_conf.update(p.readConfiguration(f))
    #now if we still have a config file update what the configuration with it
    
    if isinstance(config_file, basestring):
        if config_file == '-':
            #reading from stdin
            complete_conf.update(p.readConfiguration(sys.stdin))
            
        elif config_file is not None:
            with open(config_file, 'r') as f:
                complete_conf.update(p.readConfiguration(f))
    elif config_file is not None:
        #if it's not a string and is something, we asume is something that can be read from
        complete_conf.update(p.readConfiguration(config_file))

    #update with user defaults if desired
    complete_conf.update(p.__parameters__.parseArguments(arguments, check_errors=False))
    #we haven't check for errors because we might have a half implemented configuration
    #some required field might have already been setup (user/system defaults, files, etc)
    #but better if we check them
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
:param config_file: path to a file  where the setup will be stored. If None, the default user dependent one will be used. 
                    This will be completely skipped if ``use_user_defaults`` is ``False``.
:returns: The path to the configuration file that was written."""
    plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    p = getPluginInstance(plugin_name, user)
    complete_conf = p.setupConfiguration(config_dict=config_dict, check_cfg=False, substitute=False)
    
    if config_file is None:
        #make sure the required directory structure and data is in place
        user.prepareDir()
         
        config_file = user.getUserToolConfig(plugin_name, create=True)

    if config_file == '-':
        p.saveConfiguration(sys.stdout, config_dict=complete_conf)
    else:
        with open(config_file, 'w') as f:
            p.saveConfiguration(f, config_dict=complete_conf)
    
    return config_file

        
def __preview_copy(source_path, dest_path):
    """
    Copy images for preview
    :type source_path: str
    :param source_path: the source
    :type dest_path: str
    :param dest_path: the destination
    """
    shutil.copyfile(source_path, dest_path)

def __preview_convert(source_path, dest_path):
    """
    Converts images
    :type source_path: str
    :param source_path: the file name of the file to convert
    :type dest_path: str
    :param dest_path: The file name of the converted file
    """
    
    # a not very pythonic work-around
    command = ['convert', source_path, dest_path]
    sub.call(command)

    # The following is preferable when supported by the installed PIT version
    # im = Image.open(source_path)
    # im.save(dest_path)

def __preview_generate_name(plugin_name, file_name, metadata):
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
    random_suffix = ''.join(random.choice(string.letters) for i in xrange(8))

    ctime = metadata.get('timestamp', '')
    
    if ctime:
        time_string = datetime.datetime.fromtimestamp(ctime).strftime('%Y%m%d_%H%M%S') 
        ctime = '%s_' % time_string
        
        
    return plugin_name + '_' + ctime + random_suffix

def __preview_unique_file(plugin_name, file_name, ext, metadata):
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
    path = config.PREVIEW_PATH
    subdir = datetime.datetime.now().strftime('%Y%m%d')
    name = __preview_generate_name(plugin_name, file_name, metadata) 
    name = name + ext
    full_path = os.path.join(path, subdir)
    full_name = os.path.join(full_path, name)
    
    if not os.path.isdir(full_path):
        utils.supermakedirs(full_path, 0777)
        
    if os.path.isfile(full_name):
        return __preview_unique_file(plugin_name, file_name, ext, metadata)
    
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
    
    for file_name in result:
        metadata = result[file_name]
        todo=metadata.get('todo', '')
        
        
        if todo == 'copy':
            ext = os.path.splitext(file_name)[-1]
            target_name = __preview_unique_file(plugin_name, file_name, ext, metadata)
            todo_list.append((__preview_copy, file_name, target_name))
            metadata['preview_path'] = target_name
            
        elif todo == 'convert':
            target_name = __preview_unique_file(plugin_name, file_name, '.png', metadata)
            todo_list.append((__preview_convert, file_name, target_name))
            metadata['preview_path'] = target_name
            
        result[file_name]=metadata

    if todo_list:
        p =  Pool(config.NUMBER_OF_PROCESSES)
        p.map(utils.mp_wrap_fn, todo_list)
            

def runTool(plugin_name, config_dict=None, user=None, scheduled_id=None):
    """Runs a tool and stores this "run" in the :class:`evaluation_system.model.db.UserDB`.
    
:type plugin_name: str
:param plugin_name: name of the referred plugin.
:type config_dict: dict or metadict 
:param config_dict: The configuration used for running the tool. If is None, the default configuration will be stored, 
    this might be incomplete.
:type user: :class:`evaluation_system.model.user.User`
:param scheduled_id: if the process is already scheduled then put the row id here
"""
    
    plugin_name = plugin_name.lower()
    if user is None: user = User()
    
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
        #at this stage we want to resolve or tokens and perform some kind of sanity check before going further 
        complete_conf = p.setupConfiguration(config_dict=config_dict, recursion=True)
        
    
     
    log.debug('Running %s with %s', plugin_name, complete_conf)
    
    rowid = 0
    
    if scheduled_id:
        user.getUserDB().upgradeStatus(scheduled_id,
                                       user.getName(),
                                       db._status_running)
        rowid = scheduled_id
    elif user:
        rowid = user.getUserDB().storeHistory(p,
                                              complete_conf,
                                              user.getName(),
                                              db._status_running)
        
    try:
        #In any case we have now a complete setup in complete_conf
        result = p._runTool(config_dict=complete_conf)

        # save results when existing
        if result is None:
            user.getUserDB().upgradeStatus(rowid,
                                            user.getName(),
                                            db._status_finished_no_output)
            
        else:
            # create the preview
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
                                           db._status_finished)
    
    except:
        user.getUserDB().upgradeStatus(rowid,
                                       user.getName(),
                                       db._status_broken)

        raise 
    
    return result

def scheduleTool(plugin_name, slurmoutdir=None, config_dict=None, user=None):
    """Schedules  a tool and stores this "run" in the :class:`evaluation_system.model.db.UserDB`.
    
:type plugin_name: str
:param plugin_name: name of the referred plugin.
:type slurmoutdir: string 
:param slurmoutdir: directory for the output
:type config_dict: dict or metadict 
:param config_dict: The configuration used for running the tool. If is None, the default configuration will be stored, 
    this might be incomplete.
:type user: :class:`evaluation_system.model.user.User`
:param scheduled_id: if the process is already scheduled then put the row id here
"""
    
    plugin_name = plugin_name.lower()
    if user is None: user = User()
    
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
        #at this stage we want to resolve or tokens and perform some kind of sanity check before going further 
        complete_conf = p.setupConfiguration(config_dict=config_dict, recursion=True)
        
    
     
    log.debug('Schedule %s with %s', plugin_name, complete_conf)
    
    slurmindir = os.path.join(user.getUserSchedulerInputDir(), user.getName())
    if not os.path.exists(slurmindir):
        utils.supermakedirs(slurmindir, 0777)

    rowid = user.getUserDB().storeHistory(p,
                                          complete_conf,
                                          user.getName(),
                                          db._status_not_scheduled)
    
       
    full_path = os.path.join(slurmindir, p.suggestSlurmFileName())

    # set the SLURM output directory
    if not slurmoutdir:
        slurmoutdir = user.getUserSchedulerOutputDir()
        slurmoutdir = os.path.join(slurmoutdir, plugin_name)

    if not os.path.exists(slurmoutdir):
        utils.supermakedirs(slurmoutdir, 0777)

    with open(full_path, 'w') as fp:
        p.writeSlurmFile(fp,
                         scheduled_id=rowid,
                         user=user,
                         slurmoutdir=slurmoutdir)
            
    # create the batch command
    command = ['/bin/bash',
               '-c',
               '%s %s --uid=%s %s\n' % (config.SCHEDULER_COMMAND,
                                        config.SCHEDULER_OPTIONS,
                                        user.getName(),
                                        full_path)
              ]

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

    return (rowid, slurm_out)


def getHistory(plugin_name=None, limit=-1, since = None, until = None, entry_ids=None, user=None):
    """Returns the history from the given user.
This is just a wrapper for the defined db interface accessed via the user object.
See :class:`evaluation_system.model.db.UserDB.getHistory` for more information on this interface."""
    if plugin_name is not None: plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    return user.getUserDB().getHistory(plugin_name, limit, since=since, until=until, entry_ids=entry_ids, uid = user.getName())

def getCommandString(entry_id, user=None, command_name='analyze', command_options='--tool'):
    """
    Return the parameter string of a history entry.
    :type entry_id: integer
    :param entry_id: the history id
    :type user: User
    :param user: A user to access the database
    """
    if user is None: user = User()
    
    h = user.getUserDB().getHistory(entry_ids=int(entry_id))
    
    return getCommandStringFromRow(h[0], command_name, command_options)
    

def getCommandStringFromRow(history_row, command_name='analyze', command_options='--tool'):
    """
    Return the parameter string of a history entry.
    :type history_row: row
    :param history_row: row of the history table
    """
        
    result = "%s %s %s" % (command_name, command_options, history_row.tool_name)

    configuration = history_row.configuration

    # find lists
    re_list_pattern = "^\[.*\]$"
    re_list = re.compile(re_list_pattern)
    
    for k in configuration.keys():
        value = configuration[k]

        if not value is None:
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
    h = getHistory(plugin_name=plugin_name , entry_ids=entry_id, user=user)

    # only one row should be selected
    row = h[0]

    # scheduled jobs only
    if row.status != db._status_scheduled:
        raise Exception("This is not a scheduled job (status %i)!" % row.status)
            
    return row.configuration
    
    
