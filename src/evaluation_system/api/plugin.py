'''

.. moduleauthor:: estani <estanislao.gonzalez@met.fu-berlin.de>


This module defines the basic objects for implementing a plug-in.
'''

import abc
import subprocess as sub
import os
import sys
import stat
import shutil
import re
from time import time
from datetime import datetime
from ConfigParser import SafeConfigParser
from exceptions import ValueError
import logging
log = logging.getLogger(__name__)
from pyPdf import PdfFileReader

from evaluation_system.model.user import User
from evaluation_system.misc.utils import TemplateDict
from evaluation_system.misc import config
from evaluation_system.model.solr_core import SolrCore

__version__ = (1,0,0)

class ConfigurationError(Exception):
    """Signals the configuration failed somehow."""
    pass

        
class PluginAbstract(object):
    """This is the base class for all plug-ins. It is the only class that needs to be inherited from when implementing a plug-in.
    
From it, you'll need to implement the few attributes and/or methods marked as abstract with the decorator
``@abc.abstractproperty`` or ``@abc.abstractmethod``. If you don't you'll get a message informing you which methods
and or variables need to be implemented. Refer to their documentation to know what they should do.

As usual, you may overwrite all methods and properties defined in here, but you'll be breaking the contract
between the methods so you'll have to make sure it doesn't break anything else. Please write some tests
for your own class that checks it is working as expected. The best practice is to use what is provided as is and only
implement what is required (and more, if you need, just don't overwrite any methods/variable if you don't need to)

This very short example shows a complete plug-in. Although it does nothing it already show the most important part,
the :class:`evaluation_system.api.parameters.ParameterDictionary` used for defining meta-data on the parameters::

    from evaluation_system.api import plugin, parameters
    
    class MyPlugin(plugin.PluginAbstract):
        __short_description__ = "MyPlugin short description (just to know what it does)" 
        __version__ = (0,0,1)
        __parameters__ =  parameters.ParameterDictionary(
                            parameters.Integer(name='number', help='This is an optional configurable int variable named number without default value and this description'),
                            parameters.Float(name='the_number',mandatory=True, help='A required float value without default'),
                            parameters.Bool(name='really', default=False, help='a boolean parameter named really with default value of false'), 
                            parameters.String(name='str')) #a simple optional string without any other information
    
        def runTool(self, config_dict=None):
            print "MyPlugin", config_dict

If you need to test it use the ``EVALUATION_SYSTEM_PLUGINS`` environmental variable to point to the source directory and package.
For example assuming you have th source code in ``/path/to/source`` and the package holding the class implementing :class:`evaluation_system.api.plugin` is
``package.plugin_module`` (i.e. its absolute file path is ``/path/to/source/package/plugin_module.py``), you would tell the system how to find
the plug-in by issuing the following command (bash & co)::

    export EVALUATION_SYSTEM_PLUGINS=/path/to/source,package.plugin_module

Use a colon to separate multiple items::

    export EVALUATION_SYSTEM_PLUGINS=/path1,plguin1:/path2,plugin2:/path3,plugin3

By telling the system where to find the packages it can find the :class:`evaluation_system.api.plugin` implementations. The system just loads the packages and get to the classes using the :py:meth:`class.__subclasses__` method. The reference speaks about *weak references* so it's not clear if (and when) they get removed. 
We might have to change this in the future if it's not enough. Another approach would be forcing self-registration of a class in the :ref:`__metaclass__ <python:datamodel>` attribute when the class is implemented. 

For more general (and less technical) information refer to the wiki: https://code.zmaw.de/projects/miklip-d-integration/wiki
"""
    
    __metaclass__ = abc.ABCMeta

    special_variables = None
    """This dictionary is used to resolve the *special variables* that are available
to the plug-ins for defining some values of their parameters in a standardize manner.
These are initialized per user and plug-in. The variables are:

================== ===================================================================================
   Variables          Description
================== ===================================================================================
USER_BASE_DIR      Absolute path to the central directory for this user in the evaluation system. 
USER_OUTPUT_DIR    Absolute path to where the output data for this user is stored. 
USER_PLOTS_DIR     Absolute path to where the plots for this user is stored. 
USER_CACHE_DIR     Absolute path to where the cached data for this user is stored.
USER_UID           The users UID 
SYSTEM_DATE        Current date in the form YYYYMMDD (e.g. 20120130). 
SYSTEM_DATETIME    Current date in the form YYYYMMDD_HHmmSS (e.g. 20120130_101123). 
SYSTEM_TIMESTAMP   Milliseconds since epoch (i.e. a new number every millisecond, e.g. 1358929581838).
SYSTEM_RANDOM_UUID A random UUID string (e.g. 912cca21-6364-4f46-9b03-4263410c9899). 
================== ===================================================================================

A plug-in/user might then use them to define a value in the following way::

    output_file='$USER_OUTPUT_DIR/myfile_${SYSTEM_DATETIME}blah.nc'

"""

    tool_developer = None

    def __init__(self, *args, **kwargs):
        """Plugin main constructor. It is designed to catch all calls. It accepts a ``user``
argument containing an :class:`evaluation_system.model.user.User` representing the user for 
which this plug-in will be created. It is used here for setting up the user-defined configuration but 
the implementing plug-in will also have access to it. If no user is provided an object representing 
the current user, i.e. the user that started this program, is created.""" 
        if 'user' in kwargs:
            self._user = kwargs.pop('user')
        else:
            self._user = User()
            
        #this construct fixes some values but allow others to be computed on demand
        #it holds the special variables that are accessible to both users and developers
        #self._special_vars = SpecialVariables(self.__class__.__name__, self._user)
        
        from functools import partial
        from uuid import uuid4
        plugin_name, user = self.__class__.__name__, self._user
        self._special_variables = TemplateDict(
            USER_BASE_DIR      = user.getUserBaseDir,
            USER_CACHE_DIR     = partial(user.getUserCacheDir, tool=plugin_name, create=False),
            USER_PLOTS_DIR     = partial(user.getUserPlotsDir, tool=plugin_name, create=False),
            USER_OUTPUT_DIR    = partial(user.getUserOutputDir, tool=plugin_name, create=False),
            USER_UID           = user.getName,
            SYSTEM_DATE        = lambda: datetime.now().strftime('%Y%m%d'),
            SYSTEM_DATETIME    = lambda: datetime.now().strftime('%Y%m%d_%H%M%S'),
            SYSTEM_TIMESTAMP   = lambda: str(long(time() * 1000)),
            SYSTEM_RANDOM_UUID = lambda: str(uuid4()))
        
    @abc.abstractproperty
    def __version__(self):
        """``@abc.abstractproperty`` 

A 3-value tuple representing the version of the plug-in. E.g. ``(1, 0, 3)`` that's (major, minor, build)."""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def __short_description__(self):
        """``@abc.abstractproperty``

A short description of this plug-in. It will be displayed to the user in the help and
when listing all plug-ins."""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def __parameters__(self):
        """``@abc.abstractproperty``

A :class:`evaluation_system.plugin.parameters.ParametersDictionary` containing the definition of all known configurable 
parameters for the implementing class."""
        raise NotImplementedError("This attribute must be implemented")
        
    @abc.abstractmethod
    def runTool(self, config_dict = None):
        """``@abc.abstractmethod``

Starts the tool with the given configuration. It is expected to return a :class:`metadict` with the
paths to the created files and some info about them. This can be directly handled by passing just
a list (or anything iterable) to :class:`prepareOutput` .


:param config_dict: A dict with the current configuration (param name, value) with which the tool will be run
:return: see and use self.prepareOutput([<list_of_created_files>])"""
        raise NotImplementedError("This method must be implemented")
    
    def _runTool(self, config_dict = None, unique_output=True):
        #start = time()
        if unique_output:
            from evaluation_system.api.parameters import Directory
            for key, param in self.__parameters__.iteritems():
                tmp_param = self.__parameters__.get_parameter(key)
                if isinstance(tmp_param, Directory):
                    config_dict[key] = os.path.join(config_dict[key], str(self.rowid))
        result = self.runTool(config_dict=config_dict)
        #end = time()
        
        #length_seconds = end - start
        #datetime.fromtimestamp(start)
        return result
    
    def linkmydata(self,outputdir=None):
        """Link the CMOR Data Structure of any output created by a tool
           crawl the directory and ingest the directory with solr::
            :param outputdir: cmor outputdir that where created by the tool.
            :return: nothing
        """
        user = self._user
        workpath  = os.path.join(user.getUserBaseDir(),'CMOR4LINK')
        
        rootpath  = config.get('project_data')
        solr_in   = config.get('solr.incoming')
        solr_bk   = config.get('solr.backup')
        solr_ps   = config.get('solr.processing')
        
        # look for tool in tool
        toolintool = re.compile(r'^(?P<tool>[\w-]+)(-(\d+)|(none)-(?P<project>[\w_]+)-(?P<product>[\w_]+)$)')
        # Maybe os.walk for multiple projects or products
        if len(os.listdir(outputdir)) == 1:
            project = os.listdir(outputdir)[0]
            # link?
        if len(os.listdir(os.path.join(outputdir,project))) == 1:
            product = os.listdir(os.path.join(outputdir,project))[0]
        new_product = '%s-%s-%s-%s' % (self.__class__.__name__.lower(),self.rowid,project,product)
        if re.match(toolintool,product):
            nproduct = re.match(toolintool,product).group('product')
            nproject = re.match(toolintool,product).group('project')
            ntool    = '-%s' % re.match(toolintool,product).group('tool')
            new_product = '%s%s%s-%s-%s' % (self.__class__.__name__.lower(),ntool,self.rowid,nproject,nproduct)
        # Link section
        if os.path.islink(os.path.join(rootpath,user.getName())):
            workpath = os.path.join(os.path.dirname(os.path.join(rootpath,user.getName())), os.readlink(os.path.join(rootpath,user.getName())))
        else:
           if not os.path.isdir(workpath): os.makedirs(workpath)
           os.symlink(workpath, os.path.join(rootpath,user.getName()))
        os.symlink(os.path.join(outputdir,project,product), os.path.join(workpath,new_product))
        
        # Prepare for solr
        crawl_dir=os.path.join(rootpath,user.getName(),new_product)
        now = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output = os.path.join(solr_in,'solr_crawl_%s.csv.gz' %(now))
        
        # Solr part with move orgy
        SolrCore.dump_fs_to_file(crawl_dir, output)
        shutil.move(os.path.join(solr_in,output),os.path.join(solr_ps,output))
        hallo = SolrCore.load_fs_from_file(dump_file=os.path.join(solr_ps,output))
        shutil.move(os.path.join(solr_ps,output),os.path.join(solr_bk,output))
        
    def prepareOutput(self, output_files):
        """Prepare output for files supposedly created. This method checks the files exist
and returns a dictionary with information about them::

    { <absolute_path_to_file>: {
        'timestamp': os.path.getctime(<absolute_path_to_file>),
        'size': os.path.getsize(<absolute_path_to_file>)
        }
    }

Use it for the return call of runTool.
    
:param output_files: iterable of strings or single string with paths to all files that where created by the tool.
:return: dictionary with the paths to the files that were created as key and a dictionary as value.
    """
        result = {}
        if isinstance(output_files, basestring): output_files = [output_files]
        for file_path in output_files:
            metadata = {}

            # we expect a meta data dictionary
            if isinstance(output_files, dict):
                metadata = output_files[file_path]
                if not isinstance(metadata, dict):
                    raise ValueError('Meta information must be of type dict')

            if os.path.isfile(file_path):
                self._extend_output_metadata(file_path, metadata)
                result[os.path.abspath(file_path)] = metadata
            elif os.path.isdir(file_path):
                #ok, we got a directory, so parse the contents recursively
                for file_path in [os.path.join(r,f) for r,_,files in os.walk(file_path) for f in files]:
                    filemetadata = metadata.copy()
                    self._extend_output_metadata(file_path, filemetadata)
                    
                    # update meta data with user entries
                    usermetadata = result.get(os.path.abspath(file_path), {})
                    filemetadata.update(usermetadata)
                    
                    result[os.path.abspath(file_path)] = filemetadata
            else:
                result[os.path.abspath(file_path)] = metadata
        return result

    def _extend_output_metadata(self, file_path, metadata):
        fstat=os.stat(file_path)
              
        if 'timestamp' not in metadata:
            metadata['timestamp'] = fstat[stat.ST_CTIME]
            # metadata['timestamp'] = os.path.getctime(file_path)
        if 'size' not in metadata:
            metadata['size'] = fstat[stat.ST_SIZE]
            # metadata['size'] = os.path.getsize(file_path)
        if 'type' not in metadata:    
            ext = os.path.splitext(file_path)
            if ext:
                ext = ext[-1].lower()
                if ext in '.jpg .jpeg .png .gif'.split():
                    metadata['type'] = 'plot'
                    metadata['todo'] = 'copy'
                    
                if ext in '.tif .svg .ps .eps'.split():
                    metadata['type'] = 'plot'
                    metadata['todo'] = 'convert'
                
                if ext == '.pdf':
                    #If pdfs have more than one page we don't convert them, 
                    #instead we offer a download link
                    pdf = PdfFileReader(open(file_path,'rb'))
                    num_pages = pdf.getNumPages()
                    metadata['type'] = 'pdf'
                    if num_pages > 1:
                        metadata['todo'] = 'copy'
                    else:
                        metadata['todo'] = 'convert'
                        
                if ext in '.tex'.split():
                    metadata['type'] = 'plot'
                    
                elif ext in '.nc .bin .ascii'.split():
                    metadata['type'] = 'data'
                if ext in ['.zip']:
                    metadata['type'] = 'pdf'
                    metadata['todo'] = 'copy'                     
                           
    
    def getHelp(self, width=80):
        """This method uses the information from the implementing class name, :class:`__version__`, 
:class:`__short_description__` and :class:`__config_metadict__` to create a proper help.
Since it returns a string, the implementing class might use it and extend it if required. 

:param width: Wrap text to this width.
:returns: a string containing the help."""
        if hasattr(self,'__long_description__'):
            help_txt = self.__long_description__
        else:
            help_txt = self.__short_description__
        return '%s (v%s): %s\n%s' % (self.__class__.__name__, '.'.join([str(i) for i in self.__version__]), \
                                     help_txt, self.__parameters__.getHelpString())
        
    def getCurrentConfig(self, config_dict = {}):
        """
:param config_dict: the dict containing the current configuration being displayed. 
                    This info will update the default values.
:return: the current configuration in a string for displaying."""
        max_size= max([len(k) for k in self.__parameters__])
        
        current_conf = []
        config_dict_resolved = self.setupConfiguration(config_dict=config_dict, check_cfg=False)
        config_dict_orig = dict(self.__parameters__)
        config_dict_orig.update(config_dict)
        
        def show_key(key):
            "This functions formats the results depending on whether the values contain variables or not."
            if config_dict_resolved[key] == config_dict_orig[key]:
                return  config_dict_orig[key]
            else:
                return '%s [%s]' % (config_dict_orig[key], config_dict_resolved[key]) 
        
        for key in self.__parameters__:
            line_format = '%%%ss: %%s' % max_size
            
            
            if key in config_dict:
                #user defined
                curr_val = show_key(key)
            else:
                #default value
                default_value = self.__parameters__[key]
                if default_value is None: 
                    if self.__parameters__.get_parameter(key).mandatory:
                        curr_val = '- *MUST BE DEFINED!*'
                    else:
                        curr_val = '-'
                else:
                    curr_val = '- (default: %s)' % show_key(key)
                    

            
            current_conf.append(line_format % (key, curr_val))
    
        return '\n'.join(current_conf)

    def getClassBaseDir(self):
        """:returns: the absolute path to the module defining the class implementing this plug-in."""
        subclass_file = os.path.abspath(sys.modules[self.__module__].__file__)
        return os.path.join(*self._splitPath(subclass_file)[:-len(self.__module__.split('.'))])

    def getCurrentUser(self):
        """:returns: the :class:`evaluation_system.model.user.User` for which this instance was generated."""
        return self._user
        
    def _parseConfigStrValue(self, param_name, str_value, fail_on_missing=True):
        """Try to parse the string in ``str_value`` into the most appropriate value according 
to the parameter logic.

The string *None* will be mapped to the value ``None``. On the other hand the quoted word *"None"* will remain as the
string ``"None"`` without any quotes.

:param param_name: Parameter name to which the string belongs.
:type param_name: str
:param str_value: The string that will be parsed.
:type str_value: str
:param fail_on_missing: If the an exception should be risen in case the param_name is not found in :class:`__parameters__`
:type fail_on_missing: bool
:return: the parsed string, or the string itself if it couldn't be parsed, but no exception was thrown.
:raises: ( :class:`ConfigurationError` ) if parsing couldn't succeed.
"""
        
        if str_value == "None": return None
        elif str_value == '"None"': str_value = "None"
        
        if self.__parameters__ is None or (not fail_on_missing and param_name not in self.__parameters__):
            #if there's no dictionary reference or the param_name is not in it and we are not failing
            #just return the str_value 
            return str_value
        
        else:
            return self.__parameters__.get_parameter(param_name).parse(str_value) 
  
  
        
    def setupConfiguration(self, config_dict = None, check_cfg = True, recursion=True, substitute=True):
        """Defines the configuration required for running this plug-in. 
If not a dictionary will be returned but with all indirections being resolved. E.g.::

    dict(a=1, b='1.txt', c='old_1.txt') == setupConfiguration(config_dict=dict(a=1, b='$a.txt', c='old_$b'))

Basically the default values from :class:`__parameters__` will be updated with the values from ``config_dict``.
There are some special values pointing to user-related managed by the system defined in :class:`evaluation_system.model.user.User.getUserVarDict` .
 
:param config_dic: dictionary with the configuration to be used when generating the configuration file.
:type config_dic: dict or :class:`metadict`
:param check_cfg: whether the method checks that the resulting configuration dictionary (i.e. the default 
                  updated by `config_dict`) has no None values after all substituions are made.
:type check_cfg: bool
:param recursion: Whether when resolving the template recursion will be applied, i.e. variables can be set
                  with the values of other variables, e.g. ``recursion && a==1 && b=="x${a}x" => f(b)=="x1x"`` 
:type recursion: bool
:return:  a copy of self.self.__config_metadict__ with all defaults values plus those provided here.
        """
        if config_dict:
            conf = dict(self.__parameters__) 
            conf.update(config_dict)
            config_dict = conf
        else:
            config_dict = dict(self.__parameters__)
        
        if substitute:
            results = self._special_variables.substitute(config_dict, recursive=recursion)
        else:
            results = config_dict.copy()

        if check_cfg:
            self.__parameters__.validate_errors(results, raise_exception=True)
        
        return results
   
    def readFromConfigParser(self, config_parser):
        """Reads a configuration from a config parser object.
The values are assumed to be in a section named just like the class implementing this method.
        
:param config_parser: From where the configuration is going to be read.
:type config_parser: ConfigParser.RawConfigParser
:return: a :class:`metadict` which is a clone of :class:`__config_metadict__` (if available) updated with the
         information found in the config Parser"""
        
        section = self.__class__.__name__
        #create a copy of metadict
        result = dict(self.__parameters__)
        #we do this to avoid having problems with the "DEFAULT" section as it might define
        #more options that what this plugin requires
        keys = set(result).intersection(config_parser.options(section))
        #update values as found in the configuration
        for key in keys:
            #parse the value as good as possible
            result[key] = self._parseConfigStrValue(key, config_parser.get(section, key))
        return result
        
    def readConfiguration(self, fp):
        """Read the configuration from a file object using a SafeConfigParser. See also :class:`saveConfiguration` .

:param fp: An object with a readline argument (e.g. as return by :py:func:`open` ) from where the configuration is going to be read.
:return: a :class:`metadict` which is a clone of :class:`__config_metadict__` (if available) updated with the
         information found in ``fp``"""
        config_parser = SafeConfigParser()
        config_parser.readfp(fp)
        return self.readFromConfigParser(config_parser)

    def saveConfiguration(self, fp, config_dict=None, include_defaults=False):
        """Stores the given configuration to the provided file object.
if no configuration is provided the default one will be used.

:param fp: An object with a readline argument (e.g. as return by :py:func:`open` ) from where the configuration is going to be read.
:param config_dict: a metadict with the configuration to be stored. If none is provided the result from
                    :class:`setupConfiguration` with ``check_cfg=False`` will be used."""
        #store the section header
        if config_dict is None:
            #a default incomplete one
            config_dict = self.setupConfiguration(check_cfg = False, substitute=False)
        fp.write('[%s]\n' % self.__class__.__name__)

        import textwrap
        wrapper = textwrap.TextWrapper(width=80, initial_indent='#: ', subsequent_indent='#:  ', replace_whitespace=False,break_on_hyphens=False,expand_tabs=False)
        
        #preserve order
        for param_name in self.__parameters__:
            if include_defaults:
                param = self.__parameters__.get_parameter(param_name)
                if param.help:
                        #make sure all new lines are comments!
                        help_lines = param.help.splitlines()                    
                        if param.mandatory:
                            help_lines[0] = '[mandatory] ' + help_lines[0]
                        fp.write('\n'.join([wrapper.fill(line) for line in help_lines]))
                        fp.write('\n')
                value = config_dict.get(param_name, None)
                if value is None:
                    #means this is not setup
                    if param.mandatory:
                        value="<THIS MUST BE DEFINED!>"
                    else:
                        value=param.default
                        param_name='#'+ param_name
                fp.write('%s=%s\n\n' % (param_name, value))
                fp.flush()  #in case we want to stream this for a very awkward reason...
                
            elif param_name in config_dict:
                param = self.__parameters__.get_parameter(param_name)
                value = config_dict[param_name]
                key_help = param.help
                isMandatory = param.mandatory
                if key_help:
                        #make sure all new lines are comments!
                        help_lines = key_help.splitlines()                    
                        if isMandatory:
                            help_lines[0] = '[mandatory] ' + help_lines[0]
                        fp.write('\n'.join([wrapper.fill(line) for line in help_lines]))
                        fp.write('\n')
                if value is None:
                    #means this is not setup
                    if isMandatory:
                        value="<THIS MUST BE DEFINED!>"
                    else:
                        value=""
                        param_name='#'+ param_name
                fp.write('%s=%s\n\n' % (param_name, param.str(value)))
                fp.flush()  #in case we want to stream this for a very awkward reason...
        return fp

    def suggestSlurmFileName(self):
        """
        Return a suggestion for the SLURM file name
        :return: file name
        """
        
        filename = datetime.now().strftime('%Y%m%d_%H%M%S_') + self.__class__.__name__
        return filename
        

    def writeSlurmFile(self, fp, config_dict=None, user=None, scheduled_id=None,
                       slurmoutdir=None, unique_output=True):
        """
        Writes a file which can be executed by the SLURM scheduler
        if no configuration is provided the default one will be used.

        :param fp: An object with a readline argument (e.g. as return by :py:func:`open` ) from where the configuration is going to be read.
        :param config_dict: a metadict with the configuration to be stored. If none is provided the result from
        :param user: a user object
        :param scheduled_id: The row-id of a scheduled job in history
        :return: an object of class slurm_file
        """
        from evaluation_system.model import  slurm
        
        if user is None:
            user = self.getCurrentUser()
        
        sf = slurm.slurm_file()
        
        if scheduled_id:
            sf.set_default_options(user,
                                   self.composeCommand(scheduled_id=scheduled_id,
                                                       unique_output=unique_output),
                                   outdir=slurmoutdir)
        else:
            sf.set_default_options(user,
                                   self.composeCommand(config_dict=config_dict,
                                                       unique_output=unique_output),
                                   outdir=slurmoutdir)
        
        sf.write_to_file(fp)
        fp.flush()
        
        return sf 
    
    class ExceptionMissingParam(Exception):
        """
        An exception class if a mandatory parameter has not been set
        """
        def __init__(self, param):
            """
            Exceptions constructor
            :param param: The missing parameter
            :type param: string
            """
            Exception.__init__(self, "Parameter %s has to be set" % param)
        
    def composeCommand(self, config_dict=None, scheduled_id=None,
                       batchmode=False, email=None, caption=None,
                       unique_output=True):
        logging.debug('config dict:' + str(config_dict))
        logging.debug('scheduled_id:' + str(scheduled_id))

        cmd_param = 'analyze '
        cmd_param = 'freva --plugin '
        cmd_param += self.__class__.__name__
	# write explicitly if batchmode is requested
        cmd_param += ' --batchmode=%s' % str(batchmode)
        
        # add a given e-mail
        if email:
            cmd_param += ' --mail=%s' % email

        # the parameter string
        #cmd_param += ' --tool ' + self.__class__.__name__
       
            
        # add a caption if given
        if not caption is None:
            quote_caption = caption
            quote_caption =  caption.replace("\\", "\\\\")
            quote_caption =  quote_caption.replace("'", "'\\''")
            cmd_param += " --caption '%s'" % quote_caption

        # append the unique_output param
        cmd_param += " --unique_output %s" % unique_output

         # a scheduled id overrides the dictionary behavior
        if scheduled_id:
            cmd_param += ' --scheduled-id %i' % scheduled_id
                      
        else:
            #store the section header
            if config_dict is None:
                #a default incomplete one
                config_dict = self.setupConfiguration(check_cfg = False, substitute=False)
            else:
                config_dict = self.setupConfiguration(config_dict = config_dict, check_cfg = False, substitute=False)
        
            # compose the parameters preserve order
            for param_name in self.__parameters__:
                if param_name in config_dict:
                    param = self.__parameters__.get_parameter(param_name)
                    value = config_dict[param_name]
                    isMandatory = param.mandatory

                if value is None:
                    if isMandatory:
                        raise self.ExceptionMissingParam(param_name)
                else:
                    cmd_param += " %s=%s" % (param_name, param.str(value))

        logging.debug('Execute command:' + cmd_param)
             
        return cmd_param

        
    def call(self, cmd_string, stdin=None, stdout=None, stderr=None):
        """Simplify the interaction with the shell. It calls a bash shell so it's **not** secure. 
It means, **never** start a plug-in comming from unknown sources.

:param cmd_string: the command to be issued in a string.
:type cmd_string: str
:param stdin: This parameter became obsolete
:type stdin: None
:param stdout: This parameter became obsolete 
:type stdout: None
:param stderr: This parameter became obsolete 
:type stderr: None
:return return code: Return code of the process  
"""
        log.debug("Calling: %s", cmd_string)
        # if you enter -x to the bash options the validation algorithm
        # after calling SLURM fails. Use -x temporary for debugging only
        if log.isEnabledFor(logging.DEBUG):
            bash_opt = '-c'
        else:
            bash_opt = '-c'
            
        if stdin or stdout or stderr:
            raise  Exception('stdin, stdout and stderr are no longer supported')

        p = sub.call(['/bin/bash', bash_opt, cmd_string])

        # this is due to backward compatibility
        return ' '

    
    def _splitPath(self, path):
        """Help function to split a path"""
        rest_path = os.path.normpath(path)
        result=[]
        while rest_path:
            old_path = rest_path
            rest_path, path_item = os.path.split(rest_path)
            if old_path == rest_path:
                result.insert(0,rest_path)
                break        
            result.insert(0, path_item)
        return result
    
    
    
    def getVersion():
        import evaluation_system.model.repository as repository
    
        from inspect import getfile
        
        version = __version_cache.get(pluginname, None)
        
        if version is None:
    
            plugin = getPlugins().get(pluginname, None)
            
            srcfile = getfile(self.__class__.__name__)
        
            version = repository.getVersion(srcfile) 
            
        return version

