# encoding: utf-8

'''
databrowser - Find data

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
'''

import logging,sys
from evaluation_system.commands import FrevaBaseCommand
from evaluation_system.model.solr import SolrFindFiles

class Command(FrevaBaseCommand):
        
    _args = [
             {'name':'--debug','short':'-d','help':'turn on debugging info and show stack trace on exceptions.','action':'store_true'},
             {'name':'--help','short':'-h', 'help':'show this help message and exit','action':'store_true'},
             {'name':'--multiversion','help':'select not only the latest version but all of them','action':'store_true', 'default':False},
             {'name':'--relevant-only','help':'show only facets that filter results (i.e. >1 possible values)','action':'store_true'},
             {'name':'--batch-size','help':'Number of files to retrieve', 'type':'int', 'metavar':'N'},
             {'name':'--count-facet-values','help':'Show the number of files for each values in each facet','action':'store_true'},
             {'name':'--attributes','help':'retrieve all possible attributes for the current search instead of the files','action':'store_true'},
             {'name':'--all-facets','help':'retrieve all facets (attributes & values) instead of the files (same as --facet "*", or --facet all, or --facet any)','action':'store_true'},
             {'name':'--facet','help':'retrieve these facets (attributes & values) instead of the files'},
             ] 
    
    __description__ = """
The query is of the form key=value. <value> might use *, ? as wildcards or any regular expression encclosed in forward slashes. Depending on your shell and the symbols used, remeber to escape the sequences properly. 
The safest would be to enclosed those in single quotes.

For Example:
    %s project=baseline1 model=MPI-ESM-LR experiment=/decadal200[0-3]/ time_frequency=*hr variable='/ta|tas|vu/'"""

    __short_description__ = '''Find data in the system'''

    def _run(self):
        
        args = self.args 
        lastargs = self.last_args 
        
        #Are we searching for facets or files?
        facets = []
        if args.all_facets:
            facets = None
        if args.facet:
            facets.append(args.facet)
        
        latest = not args.multiversion
        batch_size = args.batch_size if args.batch_size else 10
        
        search_dict = {}
        #contruct search_dict by looping over lastargs
        for arg in lastargs:
            if '=' not in arg:
                raise CommandError("Invalid format for query: %s" % arg)
            
            items = arg.split('=')
            key, value = items[0], ''.join(items[1:])

            if key not in search_dict:
                search_dict[key] = value
            else:
                if not isinstance(search_dict[key], list):
                    search_dict[key] = [search_dict[key]]
                search_dict[key].append(value)
        
        if 'version' in search_dict and latest:
            #it makes no sense to look for a specific version just among the latest
            #the speedup is marginal and it might not be what the user expects
            sys.stderr.write('Turning latest of when searching for a specific version.')
            latest = False
            
        logging.debug("Searching dictionary: %s\n", search_dict)
        #exit()
        #flush stderr in case we have something pending
        sys.stderr.flush()

        if facets != [] and not args.attributes:
            if 'facet.limit' in search_dict:
                facet_limit = int(search_dict['facet.limit'])
            else:  
                #default
                facet_limit = 1000
                search_dict['facet.limit'] = -1
                
            for att,values in SolrFindFiles.facets(facets=facets, latest_version=latest, **search_dict).items():
                
                
                #values come in pairs: (value, count)
                value_count = len(values)/2
                if args.relevant_only and value_count < 2: continue
                
                if args.count_facet_values:
                    sys.stdout.write('%s: %s' % (att, ','.join(['%s (%s)' % (v,c) for v,c in zip(*[iter(values)]*2)])))
                else:
                    sys.stdout.write('%s: %s' % (att, ','.join(values[::2])))
                
                if value_count == facet_limit: 
                    sys.stdout.write('...')
                
                sys.stdout.write('\n')
                sys.stdout.flush()
        elif args.attributes:
            #select all is none defined but this flag was set
            if facets == []: facets = None
            results = SolrFindFiles.facets(facets=facets, latest_version=latest, **search_dict)
            if args.relevant_only:
                atts = ', '.join([k for k in results if len(results[k]) > 2])
            else:
                atts = ', '.join(SolrFindFiles.facets(facets=facets, latest_version=latest, **search_dict))
            sys.stdout.write(atts)
            sys.stdout.write('\n')
            sys.stdout.flush()
        else:
            #find the files and display them
            for f in SolrFindFiles.search(batch_size=batch_size, latest_version=latest, **search_dict):
                sys.stdout.write(str(f))
                sys.stdout.write('\n')
                sys.stdout.flush()

if __name__ == "__main__":
    Command().run()







