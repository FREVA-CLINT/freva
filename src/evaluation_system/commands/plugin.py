'''
plugin - apply analysis to data

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
'''

from evaluation_system.commands import FrevaBaseCommand
import evaluation_system.api.plugin_manager as pm
from evaluation_system.model import user
import logging
import sys
from django.contrib.auth.models import User, Group
from evaluation_system.misc import config


class Command(FrevaBaseCommand):
    __short_description__ = '''Applies some analysis to the given data.'''
    __description__ = """Applies some analysis to the given data.
See https://code.zmaw.de/projects/miklip-d-integration/wiki/Analyze for more information.

The "query" part is a key=value list used for configuring the tool. It's tool dependent so check that tool help.

For Example:
    freva --plugin pca eofs=4 bias=False input=myfile.nc outputdir=/tmp/test"""

    _args = [
             {'name':'--debug','short':'-d','help':'turn on debugging info and show stack trace on exceptions.','action':'store_true'},
             {'name':'--help','short':'-h', 'help':'show this help message and exit','action':'store_true'},
             {'name':'--repos-version','help':'show the version number from the repository','action':'store_true'},
             {'name':'--caption','help':'sets a caption for the results'},
             {'name':'--save','help':'saves the configuration locally for this user.','action':'store_true'},
             {'name':'--save-config','help':'saves the configuration at the given file path', 'metavar':'FILE'},
             {'name':'--show-config','help':'shows the resulting configuration (implies dry-run).','action':'store_true'},
             {'name':'--scheduled-id','help':'Runs a scheduled job from database','type':'int', 'metavar':'ID'},
             {'name':'--dry-run','help':'dry-run, perform no computation. This is used for viewing and handling the configuration.','action':'store_true'},
             {'name':'--batchmode','help':'creates a SLURM job','metavar':'BOOL'},
             ]

    def list_tools(self):
        import textwrap
        env = self.getEnvironment()
        #we just have to show the list and stop processing
        name_width = 0
        for key in pm.getPlugins():
            name_width = max(name_width, len(key))
        offset = name_width + 2
        for key, plugin in sorted(pm.getPlugins().items()):
            lines = textwrap.wrap('%s' % plugin['description'], env['columns'] - offset)
            if not lines: lines = ['No description.']
            if len(lines) > 1:
                #multiline
                print '%s: %s' % (plugin['name'], lines[0] + '\n' + ' '*offset +('\n' + ' '*offset).join(lines[1:]))
            else:
                print '%s: %s' % (plugin['name'], lines[0])
        return 0   
   
    def auto_doc(self, message=None):
        if len(self.last_args) > 0:
            plugin = pm.getPluginInstance(self.last_args[0])
            print plugin.getHelp()
            exit(0)
        else:
            FrevaBaseCommand.auto_doc(self, message=message)
        
   
    def _run(self):
        #defaults
        options = self.args
        last_args = self.last_args
        
        #check if tool is specified
        try:
            tool_name = last_args[0]
        except IndexError:
            return self.list_tools()

        if options.repos_version:
            (repos, version) = pm.getPluginVersion(tool_name)
            print 'Repository and version of %s:\n%s\n%s' % (tool_name, repos, version)
            return 0    
        
        email = None
 
        mode = options.batchmode.lower() if options.batchmode else 'false'
        batchmode = mode in ['true', '1', 'yes', 'on', 'web',]        
        if not batchmode and mode not in ['false', '0', 'no', 'off',]:
            raise ValueError('batchmode should be set to one of those {1,0, true, false, yes, no, on, off}')  
        
        #get the plugin
        if tool_name:
            caption = None
            
            if options.caption:
                caption = pm.generateCaption(options.caption, tool_name)    
            
            if options.save_config or options.save:
                tool_dict = pm.parseArguments(tool_name,self.last_args[1:])#, use_user_defaults=use_user_defaults, config_file=cfg_file_load, check_errors=False)
                cfg_file_save = options.save_config 
                save_in = pm.writeSetup(tool_name, tool_dict, config_file=cfg_file_save)
                logging.info("Configuration file saved in %s", save_in)
            elif options.show_config:
                tool_dict = pm.parseArguments(tool_name,self.last_args[1:])#, use_user_defaults=use_user_defaults, config_file=cfg_file_load, check_errors=False)
                print pm.getPluginInstance(tool_name).getCurrentConfig(config_dict=tool_dict)
           
            elif options.scheduled_id:
                scheduled_id = options.scheduled_id
                logging.debug('Running %s as scheduled in history with ID %i', tool_name, scheduled_id)
                if not options.dry_run: 
                    pm.runTool(tool_name, scheduled_id=scheduled_id)
                                     
            else:
                #now run the tool                
                (error, warning) = pm.getErrorWarning(tool_name)
                
                if warning:
                    log.warning(warning)
                    
                if error:
                    log.error(error)

                tool_dict = pm.parseArguments(tool_name,self.last_args[1:])#, use_user_defaults=use_user_defaults, config_file=cfg_file_load)
                
                
                logging.debug('Running %s with configuration: %s', tool_name, tool_dict)
                if not options.dry_run and (not error or DEBUG):
                    
                    # we check if the user is external and activate batchmode
                    django_user = User.objects.get(username=user.User().getName())
                    if django_user.groups.filter(name=config.get('external_group', 'noexternalgroupset')).exists():
                        batchmode = True
                    
                    if batchmode:
                        [id, file] = pm.scheduleTool(tool_name,
                                                     config_dict=tool_dict,
                                                     user=user.User(email=email),
                                                     caption=caption)

                        print 'Scheduled job with history id', id
                        print 'You can view the job\'s status with the command squeue'
                        print 'Your job\'s progress will be shown with the command'
                        print 'tail -f ', file
                    else:
                        pm.runTool(tool_name, config_dict=tool_dict, caption=caption)
                        
                        # repeat the warning at the end of the run
                        # for readability don't show the warning in debug mode 
                        if warning and not DEBUG:
                            log.warning(warning)
  

            if self.DEBUG:
                logging.debug("Arguments: %s", self.last_args)
                import json
                logging.debug('Current configuration:\n%s', json.dumps(tool_dict, indent=4))
