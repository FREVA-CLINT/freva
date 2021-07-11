# encoding: utf-8

"""
databrowser - Find data

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
"""

import logging
import sys
from warnings import warn

from evaluation_system.commands import FrevaBaseCommand, CommandError
from evaluation_system.model.solr import SolrFindFiles

class Command(FrevaBaseCommand):
        
    _args = [
             {'name': '--debug', 'short': '-d', 'help': 'turn on debugging info and show stack trace on exceptions.',
              'action': 'store_true'},
             {'name': '--help', 'short': '-h', 'help': 'show this help message and exit', 'action': 'store_true'},
             {'name': '--multiversion', 'help': 'select not only the latest version but all of them',
              'action': 'store_true', 'default': False},
             {'name': '--relevant-only', 'help': 'show only facets that filter results (i.e. >1 possible values)',
              'action': 'store_true'},
             {'name': '--batch-size', 'help': 'Number of files to retrieve', 'type': 'int', 'metavar': 'N'},
             {'name': '--count-facet-values', 'help': 'Show the number of files for each values in each facet',
              'action': 'store_true'},
             {'name': '--attributes', 'help': 'retrieve all possible attributes for the current search instead of the files',
              'action': 'store_true'},
             {'name': '--all-facets', 'help': 'retrieve all facets (attributes & values) instead of the files',
              'action': 'store_true'},
             {'name': '--facet', 'help': 'retrieve these facets (attributes & values) instead of the files'},
             ] 
    
    __description__ = """
The query is of the form key=value. <value> might use *, ? as wildcards or any regular expression enclosed in forward slashes. Depending on your shell and the symbols used, remember to escape the sequences properly.
The safest would be to enclosed those in single quotes.

For Example:
    %s project=baseline1 model=MPI-ESM-LR experiment=/decadal200[0-3]/ time_frequency=*hr variable='/ta|tas|vu/'"""

    __short_description__ = '''Find data in the system'''

    def _run(self):
        kwargs = dict(all_facets=self.args.all_facets,
                      facet=self.args.facet,
                      multiversion=self.args.multiversion,
                      batch_size=self.args.batch_size or 10,
                      count_facet_values=self.args.count_facet_values,
                      attributes=self.args.attributes)
        # contruct search_dict by looping over last_args
        for arg in self.last_args:
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
        out = self.search_data(**kwargs)
        # flush stderr in case we have something pending
        sys.stderr.flush()
        if isinstance(out, dict):
            # We have facet values as return values
            for att, values in out.items():
                add = ''
                facet_limit = len(values) + 1
                if 'facet_limit' in kwargs or 'facet.limit' in kwargs:
                    add = '...'
                    try:
                        facet_limit = int(kwargs['facet_limit'])
                    except KeyError:
                        facet_limit = int(kwargs['facet.limit'])
                try:
                    keys = ','.join([f'{k} ({c})' for n, (k, c) in enumerate(values.items()) if n < facet_limit])
                except AttributeError:
                    keys = ','.join([v for n,v in enumerate(values) if n < facet_limit])
                keys += add
                sys.stdout.write(f'{att}: {keys}\n')
                sys.stdout.flush()
            return
        if self.args.attributes:
            sys.stdout.write(', '.join(out)+'\n')
            sys.stdout.flush()
            return
        for key in out:
            sys.stdout.write(str(key)+'\n')
        sys.stdout.flush()

    @staticmethod
    def search_data(*args, **search_facets):
        """Execute the solr search."""
        if args:
            raise ValueError(f"Invalid format for query: {args}")
        multiversion = search_facets.pop('multiversion', False)
        relevant_only = search_facets.pop('relevant_only', False)
        batch_size = search_facets.pop('batch_size', 10)
        count_facet_values = search_facets.pop('count_facet_values', False)
        attributes = search_facets.pop('attributes', False)
        all_facets = search_facets.pop('all_facets', False)
        facet = search_facets.pop('facet', None)
        # Are we searching for facets or files?
        facets = []
        if isinstance(facet, str):
            facet = [facet]
        if all_facets:
            facets = None
        elif facet:
            facets += [f for f in facet if f]
        latest = not multiversion
        if 'version' in search_facets and latest:
            # it makes no sense to look for a specific version just among the latest
            # the speedup is marginal and it might not be what the user expects
            warn('Turning latest off when searching for a specific version.')
            latest = False
        logging.debug("Searching dictionary: %s\n", search_facets)
        if facets != [] and not attributes:
            out = {}
            search_facets['facet.limit'] = search_facets.pop('facet_limit', -1)
            for att, values in SolrFindFiles.facets(facets=facets,
                                                    latest_version=latest,
                                                    **search_facets).items():
                # values come in pairs: (value, count)
                value_count = len(values) // 2
                if relevant_only and value_count < 2:
                    continue
                if count_facet_values:
                    out[att] = {v: c for v, c in zip(*[iter(values)]*2)}
                else:
                    out[att] = values[::2]
            return out
        if attributes:
            out = []
            # select all is none defined but this flag was set
            facets = facets or None
            results = SolrFindFiles.facets(facets=facets,
                                           latest_version=latest,
                                           **search_facets)
            if relevant_only:
                return [k for k in results if len(results[k]) > 2]
            return [k for k in results]
        return SolrFindFiles.search(batch_size=batch_size,
                                    latest_version=latest,
                                    **search_facets)

if __name__ == "__main__":  # pragma nocover
    Command().run()
