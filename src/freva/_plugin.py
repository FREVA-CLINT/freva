from warnings import warn
from evaluation_system.commands.plugin import Command
import logging


__all__ = ['plugin']

def plugin(*args,save=False,save_config=False,show_config=False,dry_run=False,batchmode=False,scheduled_id=False,repo_version=False,unique_output=False,pull_request=False,debugs=False,**facets):


    return Command.run_plugin(*args,save=save,save_config=save_config,show_config=show_config,
                              dry_run=dry_run,batchmode=batchmode,scheduled_id=scheduled_id,
                              repo_version=repo_version,unique_output=unique_output,pull_request=pull_request,debugs=debugs,**facets)
