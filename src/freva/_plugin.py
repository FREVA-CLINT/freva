from warnings import warn
from evaluation_system.commands.plugin import Command
import logging


__all__ = ['plugin']

def plugin(*args,save=False,save_config=None,show_config=False,dry_run=False,batchmode=False,scheduled_id=False,
           repo_version=False,unique_output=False,pull_request=False,debugs=False,tag=False,**facets):
    """Options:
    debugs           turn on debugging info and show stack trace on exceptions.
    repo_version       show the version number from the repository
    caption=CAPTION     sets a caption for the results
    save                saves the configuration locally for this user.
    save_config=FILE    saves the configuration at the given file path
    show_config         shows the resulting configuration (implies dry-run).
    scheduled_id=ID     Runs a scheduled job from database
    dry_run             dry-run, perform no computation. This is used for viewing and handling the configuration.
    unique_output=BOOL  If true append the freva run id to every output folder
    pull_request        issue a new pull request for the tool (developer  only!)
    tag=TAG             The git tag to pull
    """
    return Command.run_plugin(*args,save=save,save_config=save_config,show_config=show_config,
                              dry_run=dry_run,batchmode=batchmode,scheduled_id=scheduled_id,
                              repo_version=repo_version,unique_output=unique_output,pull_request=pull_request,debugs=debugs,tag=tag,**facets)
