"""
plugin - apply analysis to data

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
"""

from evaluation_system.commands import FrevaBaseCommand
import evaluation_system.api.plugin_manager as pm
from evaluation_system.model import user
import logging
from django.contrib.auth.models import User
from evaluation_system.misc import config
from evaluation_system.model.plugins.models import ToolPullRequest
import time
import optparse
log = logging.getLogger(__name__)

class Command(FrevaBaseCommand):
    __short_description__ = '''Applies some analysis to the given data.'''
    __description__ = """Applies some analysis to the given data.
See https://code.zmaw.de/projects/miklip-d-integration/wiki/Analyze for more information.

The "query" part is a key=value list used for configuring the tool. It's tool dependent so check that tool help.

For Example:
    freva --plugin pca eofs=4 bias=False input=myfile.nc outputdir=/tmp/test"""

    _args = [
             {'name': '--debug', 'short': '-d', 'help': 'turn on debugging info and show stack trace on exceptions.',
              'action': 'store_true'},
             {'name': '--help', 'short': '-h', 'help': 'show this help message and exit', 'action': 'store_true'},
             {'name': '--repos-version', 'help': 'show the version number from the repository', 'action': 'store_true'},
             {'name': '--caption', 'help': 'sets a caption for the results'},
             {'name': '--save', 'help': 'saves the configuration locally for this user.', 'action': 'store_true'},
             {'name': '--save-config', 'help': 'saves the configuration at the given file path', 'metavar': 'FILE'},
             {'name': '--show-config', 'help': 'shows the resulting configuration (implies dry-run).',
              'action': 'store_true'},
             {'name': '--scheduled-id', 'help': 'Runs a scheduled job from database', 'type': 'int', 'metavar': 'ID'},
             {'name': '--dry-run',
              'help': 'dry-run, perform no computation. This is used for viewing and handling the configuration.',
              'action': 'store_true'},
             {'name': '--batchmode', 'help': 'creates a SLURM job', 'metavar': 'BOOL'},
             {'name': '--unique_output', 'help': 'If true append the freva run id to every output folder',
              'metavar': 'BOOL', 'default': 'true'},
             {'name': '--pull-request', 'help': 'issue a new pull request for the tool (developer only!)',
              'action': 'store_true'},
             {'name': '--tag', 'help': 'The git tag to pull', 'metavar': 'TAG'}
             ]

    def list_tools(self):
        import textwrap
        env = self.getEnvironment()
        # we just have to show the list and stop processing
        name_width = 0
        for key in pm.getPlugins():
            name_width = max(name_width, len(key))
        offset = name_width + 2
       
        for key, plugin in sorted(pm.getPlugins().items()):
            lines = textwrap.wrap('%s' % plugin['description'], env['columns'] - offset)
            if not lines:
                lines = ['No description.']
            if len(lines) > 1:
                # multi-line
                print('%s: %s' % (plugin['name'], lines[0] + '\n' + ' '*offset + ('\n' + ' '*offset).join(lines[1:])))
            else:
                print('%s: %s' % (plugin['name'], lines[0]))
        return 0

    def auto_doc(self, message=None):
        if len(self.last_args) > 0:
            plugin = pm.getPluginInstance(self.last_args[0])
            print(plugin.getHelp())
            exit(0)
        else:
            FrevaBaseCommand.auto_doc(self, message=message)

    def handle_pull_request(tag, tool_name):
        
        if not tag:
            print('Missing required option "--tag"')
            return 'Missing required option "--tag"'
        # create new entry in
        freva_user = user.User()
        db_user = freva_user.getUserDB().getUserId(freva_user.getName())
        pull_request = ToolPullRequest.objects.create(
            user_id=db_user, tool=tool_name, tagged_version=tag, status='waiting'
        )

        print('Please wait while your pull request is processed')
	
        
        while pull_request.status in ['waiting', 'processing']:
            time.sleep(5)
            pull_request = ToolPullRequest.objects.get(id=pull_request.id)
            
        if pull_request.status == 'failed':
            # TODO: Better error messages, like tag not valid or other
            print('The pull request failed.\nPlease contact the admins.')
        else:
            print(f'{tool_name} plugin is now updated in the system.\nNew version: {tag}')

    def _run(self):
        # defaults
    	
    	options=self.args
    	args=[]
    	attrib=self.last_args
    	if attrib:
            args.append(attrib[0])
            attrib=self.last_args[1:]
    	
    	kwargs=dict(caption=self.args.caption,
                      save=self.args.save,
                      save_config=self.args.save_config,
                      show_config=self.args.show_config,
                      scheduled_id=self.args.scheduled_id,
                      dry_run=self.args.dry_run,
                      repo_version=self.args.repos_version,
                      unique_output=self.args.unique_output,
                      debugs=bool(self.args.debug),
                      tag=self.args.tag,
                      pull_request=self.args.pull_request)
    
        # contruct search_dict by looping over last_args
    	for arg in attrib:
            if '=' not in arg:
                raise CommandError("Invalid format for query: %s" % arg)
            items = arg.split('=')
            key, value = items[0], ''.join(items[1:])
            if key not in kwargs:
                kwargs[key] = value
            else:
                if not isinstance(kwargs[key], list):
                    kwargs[key] = [kwargs[key]]
                kwargs[key].append(value)
    	

    	Output=self.run_plugin(*args,**kwargs)

       
 	
    	if self.args.repos_version:
    	    print(Output)
    	if self.args.show_config:
    	    print(Output)    
    	
        # check if tool is specified
        
        
    @staticmethod        
    def run_plugin(*args,**search_constraints):
  
    	
    	
    	tool_name=''
    	tools=''
    	results=''
    	if not args: 
    	  
    	   com=Command()
    	   tools=Command.list_tools(com)    	
    	   return tools
    	else:
    	   tool_name=args[0]     	         
    	
    	caption = search_constraints.pop('caption', False)
    	save = search_constraints.pop('save', False)
    	save_config = search_constraints.pop('save_config',None)
    	show_config = search_constraints.pop('show_config', False)
    	scheduled_id = search_constraints.pop('scheduled_id', False)
    	dry_run = search_constraints.pop('dry_run', False)
    	batchmode = search_constraints.pop('batchmode', False)
    	repo_version= search_constraints.pop('repo_version',False)
    	unique_output=search_constraints.pop('unique_output',False)
    	pull_request=search_constraints.pop('pull_request',False)
    	tag=search_constraints.pop('tag',False)
    	debugs=search_constraints.pop('debugs',False)
    	
    	if pull_request:
            output= Command.handle_pull_request(tag,tool_name)
            return output
    	if repo_version:
    	    
    	    (repos, version) = pm.getPluginVersion(tool_name)
    	    return f'Repository and version of :{tool_name}\n{repos}\n{version}'
    	    
    	email = None
    	unique_output = unique_output.lower() if unique_output else 'true'
    	unique_output = unique_output not in ['false', '0', 'no']
    	mode = batchmode.lower() if batchmode else 'false'
    	batchmode = mode in ['true', '1', 'yes', 'on', 'web']
    	if not batchmode and mode not in ['false', '0', 'no', 'off']:
    	    raise ValueError('batchmode should be set to one of those {1,0, true, false, yes, no, on, off}')
        # get the plugin
    	tool_dict=[]
    	for k, v in search_constraints.items():
    	    tool_dict.append(f'{k}={v}')
    	      
    	if tool_name:
    	   
    	    if caption:
    	        caption = pm.generateCaption(caption, tool_name)
    	    if save_config or save:
                tool_dict = pm.parseArguments(tool_name, tool_dict)
                cfg_file_save = save_config
                save_in = pm.writeSetup(tool_name, tool_dict, config_file=cfg_file_save)
                log.info("Configuration file saved in %s", save_in)
    	    elif show_config:
                tool_dict = pm.parseArguments(tool_name, tool_dict)
                return(pm.getPluginInstance(tool_name).getCurrentConfig(config_dict=tool_dict))
    	    elif scheduled_id:
                scheduled_id = scheduled_id
                log.debug('Running %s as scheduled in history with ID %i', tool_name, scheduled_id)
                if not dry_run:
                    pm.runTool(tool_name, scheduled_id=scheduled_id,
                               unique_output=unique_output)
    	    else:
                # now run the tool
                (error, warning) = pm.getErrorWarning(tool_name)
                
                if warning:
                    log.warning(warning)
                    
                if error:
                    log.error(error)
                #print(search_constraints)
                tool_dict = pm.parseArguments(tool_name,tool_dict)
                
                log.debug('Running %s with configuration: %s', tool_name, tool_dict)
                if not dry_run and (not error or debug):
                    # we check if the user is external and activate batchmode
                    django_user = User.objects.get(username=user.User().getName())
                    if django_user.groups.filter(name=config.get('external_group', 'noexternalgroupset')).exists():
                        batchmode = True
                    
                    if batchmode:
                        [id, file] = pm.scheduleTool(tool_name,
                                                     config_dict=tool_dict,
                                                     user=user.User(email=email),
                                                     caption=caption,
                                                     unique_output=unique_output)

                        log.info('Scheduled job with history id', id)
                        log.info('You can view the job\'s status with the command squeue')
                        log.info('Your job\'s progress will be shown with the command')
                        log.info('tail -f ', file)
                    else:
                        if debugs:
                            tool_dict['debug']=True
                        else: 
                            tool_dict['debug']=False
                        log.info("running..")
                        results=pm.runTool(tool_name, config_dict=tool_dict,
                                   caption=caption, unique_output=unique_output)
                        
                        # repeat the warning at the end of the run
                        # for readability don't show the warning in debug mode 
                        if warning and not debugs:
                            log.warning(warning)

    	    if debugs:
    	        
    	        log.debug("Arguments: %s", search_constraints)
    	        import json
    	        log.debug('Current configuration:\n%s', json.dumps(tool_dict, indent=4))
            
    	    return results
