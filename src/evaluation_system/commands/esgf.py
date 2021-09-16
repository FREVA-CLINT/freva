# encoding: utf-8

"""
esgf - Command to access esgf data

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
"""

from pathlib import Path
import sys
import json
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
  
	
	# defaults
    	datasets = args.datasets
    	if args.show_facet:
	      	show_facets.append(args.show_facet)
    	download_file = args.download_script
    	query = args.query
    	kwargs = dict(show_facets=self.args.show_facet,
                      datasets=self.args.datasets,
                      download_file=self.args.download_script,
                      query=self.args.query
                      )

    	for arg in lastargs:
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
    	if DEBUG:
	     result=json.dump(kwargs)	
	     sys.stderr.write("Searching string: %s\n" % kwargs)

	# flush stderr in case we have something pending
    	sys.stderr.flush()
	                
    	out = self.search_esgf(**kwargs)
    	if args.datasets:
        	print('\n'.join(['%s - version: %s' % d for d in out]))	
    	elif args.query:
        	print('\n'.join([str(d[query]) for d in out]))
    	elif args.show_facets:
        	for facet_key in sorted(out):
	     	     if len(results[facet_key]) == 0:
    		          values = "<No Results>"
	     	     else:
    		          values = '\n\t'.join(['%s: %s' % (k, results[facet_key][k]) for k in sorted(results[facet_key])])
		 
	     	     print('[%s]\n\t%s' % (facet_key, values))
    	else:
        	print(out)
       
    def search_esgf(*args,**search_facets):
    	facets = {}
    	show_facets = []
    	result_query=[]
    	"""Command line options."""
    	
    	if args:
            raise ValueError(f"Invalid format for query: {args}")
    	show_facets = search_facets.pop('show_facets', False)
    	dataset = search_facets.pop('dataset', False)
    	query = search_facets.pop('query', False)
    	opendap = search_facets.pop('opendap', False)
    	gridftp = search_facets.pop('gridftp', False)
        
    	url_type = 'http'
    	if opendap:
    	    url_type = 'opendap'
    	if gridftp:
    	    url_type = 'gridftp'

		# find the files and display them
    	p2p = P2P()
    	
    	if download_file:
    	    download_file = Path(download_file)
    	    download_file.touch(0o755)
    	    with download_file.open('bw') as f:
    	        f.write(p2p.get_wget(**facets))
    	        return (f"Download script successfully saved to {download_file}")   # there's nothing more to be executed after this
	    
    	if datasets: 
    	    return sorted(p2p.get_datasets_names(**facets))
    	if query: 
    	    if len(query.split(',')) > 1:
		# we get multiple fields queried, return in a tructured fashion
    	        return p2p.show(p2p.get_datasets(fields=query,**facets),return_str=True)
    	    else:
		# if only one then return directly
    	        return p2p.get_datasets(fields=query, **facets)
	    		
  
	 	   	 
    	if show_facets:
    	    show_facets.append(args.show_facet)
    	    results = p2p.get_facets(show_facets, **facets)
	    # render them
    	    return sorted(results[facet_key])  	
	           
		  	
    	if not (datasets or query or show_facets):
	    # default
    	    for result in p2p.files(fields='url', **facets):
    	        for url_encoded in result['url']:
    	            url, _, access_type = url_encoded.split('|')
    	            if access_type.lower().startswith(url_type):
		    	        
    	                result_url.append(url)		     		
			
    	return result_url
	
if __name__ == "__main__":  # pragma nocover
    Command().run()
