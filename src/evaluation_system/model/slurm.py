"""
..moduleauthor: Oliver Kunst / Sebastian Illing

This module creates SLURM scheduler files
"""
from evaluation_system.misc import py27, config
from django.contrib.auth.models import User


class slurm_file(object):
    SHELL_CMD = "#!/bin/bash"
    SLURM_CMD = "#SBATCH "
    MLOAD_CMD = "module load "
    EXPORT_CMT = "EXPORT"
    
    class EntryFormat:
        """
        This class describes the format of an option for SLURM.
        """
        def __init__(self, indicator, separator):
            """
            initialize the member variables
            """
            self._ind = indicator
            self._sep = separator
            
        def indicator(self):
            """
            returns the option indicator usually "-" or "--"
            """
            return self._ind
        
        def separator(self):
            """
            returns the separator between options and value.
            (e.g. " " or "=")
            """
            return self._sep
        
        def format(self, opt, val):
            """
            this applies the saved format to a given option
            :param opt: option name
            :param val: the value of the option
            :return: a formatted string
            """
            string = str(self._ind) + str(opt) + str(self._sep)
            
            if val is not None:
                string += str(val)
                
            return string

    def __init__(self):
        """
        set the member variables
        """
        #: the options to be set, dictionary of string, (string, entry_format)
        self._options = py27.OrderedDict()
        
        #: shell variables to be set, a dictionary of string, string
        self._variables = py27.OrderedDict()

        #: a list of modules to be load
        self._modules = []
        
        #: the command to start in the scheduler
        self._cmdstring = ""
        
    def set_envvar(self, var, value):
        """
        Adds an environment variable to be set
        :param var: Variable to be set
        :param value: the value (will be converted to string)
        """
        self._variables[var] = str(value)
    
    def add_dash_option(self, opt, val):
        """
        Adds an option beginning with a dash
        :param opt: option to be set
        :param val: the value (will be converted to string)
        """
        if val is None:
            e = self.EntryFormat('-', '')
        else:
            e = self.EntryFormat('-', ' ')
            
        self._options[opt] = (val, e)
        
    def add_ddash_option(self, opt, val):
        """
        Adds an option beginning with a double dash
        :param opt: option to be set
        :param val: the value (will be converted to string)
        """
        if val is None:
            e = self.EntryFormat('--', '')
        else:
            e = self.EntryFormat('--', '=')
            
        self._options[opt] = (val, e)

    def add_module(self, mod):
        """
        Adds a module to be loaded by slurm
        :param mod: the module name
        :type mod: string
        """
        self._modules.append(mod) 
        
    def set_cmdstring(self, cmdstring):
        """
        Sets the command string to be executed by slurm
        :param cmdstring: the command
        :type cmdstring: string
        """
        self._cmdstring = cmdstring
        
    def set_default_options(self, user, cmdstring, outdir=None):
        """
        Sets the default options for a given user and a
        given command string.
        :param user: an user object
        :type user: evaluation_system.model.user.User 
        :param cmdstring: the command
        :type cmdstring: string
        """
        # read output directory from configuration
        if not outdir:
            outdir = user.getUserSchedulerOutputDir()
        email = user.getEmail()
        
        # we check if the user is external and activate batch mode
        django_user = User.objects.get(username=user.getName())
        if django_user.groups.filter(name=config.get('external_group',
                                                     'noexternalgroupset')
                                     ).exists():
            options = config.get_section('scheduler_options_extern')
        else:
            options = config.get_section('scheduler_options')

        # set the default options
        self.add_dash_option("D", outdir)
        if email:
            self.add_ddash_option("mail-user", email)
        self.set_cmdstring(cmdstring)

        self.source_file = options.pop('source')
        module_file = options.pop('module_command')
        self.add_module(module_file)

        for opt, val in options.iteritems():
            if opt.startswith('option_'):
                opt = opt.replace('option_','')
                if val == 'None':
                    self.add_ddash_option(opt,None)
                else:
                    self.add_ddash_option(opt, val)

    def write_to_file(self, fp):
        """
        Write the configuration to the SLURM scheduler to a given file handler
        
        :param fp: file to write to
        :type fp: file handler
        """
        # Execute with bash
        fp.write(self.SHELL_CMD + "\n")
        
        # Workaround for Slurm in www-miklip
        # fp.write("source /client/etc/profile.miklip\n")
       
        # Workaround for Slurm on fu
        fp.write("source %s\n" % self.source_file) 
        # write options
        opts = self._options.items()

        for opt in opts:
            # use the stored format
            optf = opt[1][1]
            option = opt[0]
            value = opt[1][0]
            
            string = self.SLURM_CMD + optf.format(option, value) + "\n"
            fp.write(string)
            
        # write the modules to be loaded
        for mod in self._modules:
            fp.write(self.MLOAD_CMD + mod + "\n")
            
        # variables to export
        variables = self._variables.items()
        
        for var in variables:
            fp.write("%s %s=%s" % (self.EXPORT_CMT, var[0], var[1]) + "\n")
        
        # write the execution command
        fp.write(self._cmdstring + "\n")
