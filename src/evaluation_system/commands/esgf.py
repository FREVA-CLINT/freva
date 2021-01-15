# encoding: utf-8

"""
esgf - Command to access esgf data

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
"""

import sys
from evaluation_system.commands import FrevaBaseCommand
from evaluation_system.model.esgf import P2P


class Command(FrevaBaseCommand):
 
    _short_args = 'hd'
    _args = [
             {'name': '--debug', 'short': '-d', 'help': 'turn on debugging info and show stack trace on exceptions.',
              'action': 'store_true'},
             {'name': '--help', 'short': '-h', 'help': 'show this help message and exit', 'action': 'store_true'},
             {'name': '--datasets', 'help': 'List the name of the datasets instead of showing the urls.',
              'action': 'store_true'},
             {'name': '--show-facet', 'help': '<list> List all values for the given facet (might be defined multiple times). The results show the possible values of the selected facet according to the given constraints and the number of *datasets* (not files) that selecting such value as a constraint will result (faceted search)',
              'metavar': 'FACET'},
             {'name': '--opendap', 'help': 'List the name of the datasets instead of showing the urls.',
              'action': 'store_true'},
             {'name': '--gridftp',
              'help': 'Show Opendap endpoints instead of the http default ones (or skip them if none found)',
              'action': 'store_true'},
             {'name': '--download-script',
              'help': '<file> Download wget_script for getting the files instead of displaying anything (only http)',
              'metavar': 'FILE'},
             {'name': '--query', 'help': '<list> Display results from <list> queried fields'},
             ] 

    __short_description__ = '''Browse ESGF data and create wget script'''
    __description__ = """
The query is of the form key=value. the key might be repeated and/or negated with the 
'_not_' suffix (e.g. model_not_=MPI-ESM-LR experiment=decadal2000 experiment=decadal2001)

Simple query:
    freva --esgf model=MPI-ESM-LR experiment=decadal2001 variable=tas distrib=False
    
The search API is described here: http://www.esgf.org/wiki/ESGF_Search_REST_API
Some special query keys:
distrib: (*true*, false) search globally or only at DKRZ (MPI data and replicas)
latest : (true, false, *unset*) search for the latest version, older ones or all.
replica: (true, false, *unset*) search only for replicas, non-replicas, or all.
"""
    
    def _run(self):
        """Command line options."""
        args = self.args
        lastargs = self.last_args
        DEBUG = self.DEBUG
        
        url_type = 'http'
        if args.opendap:
            url_type = 'opendap'
        if args.gridftp:
            url_type = 'gridftp'
        
        # defaults
        datasets = args.datasets
        facets = {}
        show_facets = []
        if args.show_facet:
            show_facets.append(args.show_facet)
        download_file = args.download_script
        query = args.query
        
        for arg in lastargs:
            items = arg.split('=')
            if items[0] not in facets:
                facets[items[0]] = []
            if len(items) > 1:
                facets[items[0]].append('='.join(items[1:]))
            
        if DEBUG:
            sys.stderr.write("Searching string: %s\n" % facets)

        # flush stderr in case we have something pending
        sys.stderr.flush()
        
        # find the files and display them
        p2p = P2P()
    
        if download_file:
            with open(download_file, 'w') as f:
                f.write(p2p.get_wget(**facets))
                print(f"Download script successfully saved to {download_file}")
                return 0   # there's nothing more to be executed after this
            return 1
        if datasets: 
            print('\n'.join(['%s - version: %s' % d for d in sorted(p2p.get_datasets_names(**facets))]))
        if query: 
            if len(query.split(',')) > 1:
                # we get multiple fields queried, return in a tructured fashion
                p2p.show(p2p.get_datasets(fields=query,**facets))
            else:
                # if only one then return directly
                print('\n'.join([str(d[query]) for d in p2p.get_datasets(fields=query, **facets)]))
            
        if show_facets:
            results = p2p.get_facets(show_facets, **facets)
            # render them
            for facet_key in sorted(results):
                if len(results[facet_key]) == 0:
                    values = "<No Results>"
                else:
                    values = '\n\t'.join(['%s: %s' % (k, results[facet_key][k]) for k in sorted(results[facet_key])])
                print('[%s]\n\t%s' % (facet_key, values))
        if not (datasets or query or show_facets):
            # default
            for result in p2p.files(fields='url', **facets):
                for url_encoded in result['url']:
                    url, _, access_type = url_encoded.split('|')
                    if access_type.lower().startswith(url_type):
                        print(url)

if __name__ == "__main__":  # pragma nocover
    Command().run()
