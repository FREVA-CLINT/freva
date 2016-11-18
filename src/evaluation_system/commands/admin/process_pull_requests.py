#!/usr/bin/env python

"""
process_pull_requests -- Process all pull requests for tools

@copyright:  2016 FU Berlin. All rights reserved.

@contact:    sebastian.illing@met.fu-berlin.de
"""

from evaluation_system.commands import FrevaBaseCommand, CommandError
from evaluation_system.model.plugins.models import ToolPullRequest
from evaluation_system.api import plugin_manager as pm
import os


class Command(FrevaBaseCommand):
    _args = [
        {'name': '--debug', 'short': '-d',
         'help': 'turn on debugging info and show stack trace on exceptions.', 'action': 'store_true'},
        {'name': '--help', 'short': '-h',
         'help': 'show this help message and exit', 'action': 'store_true'},
    ]

    __short_description__ = '''Process all pull requests for tools'''

    def _run(self):
        # get all pull requests
        pull_requests = ToolPullRequest.objects.filter(status='waiting')
        tools = pm.getPlugins()
        for request in pull_requests:
            try:
                print 'Processing pull request for %s by %s' % (request.tool, request.user)
                request.status = 'processing'
                request.save()
                tool_name = request.tool.lower()
                # Does tool exist?
                if tool_name not in tools.keys():
                    raise CommandError, 'Plugin %s does not exist' % request.tool

                # get repo path
                path = '/'.join(tools[tool_name]['plugin_module'].split('/')[:-1])
                exit_code = os.system(
                    'cd %s; git pull; git checkout -b version_%s %s' % (path, request.tagged_version,
                                                                        request.tagged_version)
                )
                if exit_code > 1:
                    # Probably branch exists already
                    # Try to checkout old branch
                    exit_code = os.system(
                        'cd %s; git checkout version_%s ' % (path, request.tagged_version)
                    )
                    if exit_code > 1:
                        raise CommandError, 'Something went wrong, please contact the admins'

                request.status = 'success'
                request.save()

            except CommandError as e:
                request.status = 'failed'
                request.save()
                raise e


if __name__ == "__main__":  # pragma: nocover
    Command().run()
