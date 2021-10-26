# encoding: utf-8

"""
esgf - Command to access esgf data

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
"""

from pathlib import Path
import sys
import json
import logging
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
    	
    	
    	kwargs = dict(show_facets=self.args.show_facet,
                      datasets=self.args.datasets,
                      download_script=self.args.download_script,
                      query=self.args.query
                      )
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
    	filtered = {k: v for k, v in kwargs.items() if v is not None}
    	kwargs.clear()
    	kwargs.update(filtered)
         
    	
    	if self.DEBUG:
	     result=json.dumps(kwargs)	
	     sys.stderr.write("Searching string: %s\n" % kwargs)

	# flush stderr in case we have something pending
    	sys.stderr.flush()
	                
    	out = self.search_esgf(**kwargs)
    	print(type(out))
    	if self.args.datasets:
        	print('\n'.join(['%s - version: %s' % d for d in out]))	
    	elif self.args.query:
    		if len(self.args.query.split(',')) > 1: 
        		print('\n'.join([str(out)]))
    		else:
        		print('\n'.join([str(d[query]) for d in dict(out)])) # for d in out]))
    	elif self.args.show_facet:
        	for facet_key in sorted(out):
	     	     if len(out[facet_key]) == 0:
    		          values = "<No Results>"
	     	     else:
    		          values = '\n\t'.join(['%s: %s' % (k, out[facet_key][k]) for k in sorted(out[facet_key])])
		 
	     	     print('[%s]\n\t%s' % (facet_key, values))
    	elif self.args.download_script:
    		print(out)
    	else:
        	print('\n'.join([str(d) for d in out]))
        	
    @staticmethod   
    def search_esgf(**search_constraints):
    	facets = {}
    	show_facet = []
    	result_query=[]
    	result_url=[]
    	"""Command line options."""
    	
    	#if args:
        #    raise ValueError(f"Invalid format for query: {args}")
    	show_facets = search_constraints.pop('show_facets', False)
    	dataset = search_constraints.pop('dataset', False)
    	query = search_constraints.pop('query', False)
    	download_script = search_constraints.pop('download_script', False)
    	opendap = search_constraints.pop('opendap', False)
    	gridftp = search_constraints.pop('gridftp', False)
        
    	url_type = 'http'
    	if opendap:
    	    url_type = 'opendap'
    	if gridftp:
    	    url_type = 'gridftp'

		# find the files and display them
    	p2p = P2P()
    	
    	if download_script:
    	    download_script = Path(download_script)
    	    download_script.touch(0o755)
    	    
    	    with download_script.open('bw') as f:
    	        f.write(p2p.get_wget(**search_constraints))
    	    return (f"Download script successfully saved to {download_script}")   # there's nothing more to be executed after this
	    
    	if dataset: 
    	    return sorted(p2p.get_datasets_names(**search_constraints))
    	if query: 
    	    if len(query.split(',')) > 1:
		# we get multiple fields queried, return in a tructured fashion
    	        return p2p.show(p2p.get_datasets(fields=query,**search_constraints),return_str=True)
    	    else:
		# if only one then return directly
    	        return p2p.get_datasets(fields=query, **search_constraints)
	    		
  
	 	   	 
    	if show_facets:
    	    show_facet.append(show_facets)
    	    
    	    results = p2p.get_facets(show_facet, **search_constraints)
    	    # render them
    	    
    	    return results
	           
		  	
    	if not (dataset or query or show_facets):
	    # default
    	    
    	   
    	    for result in p2p.files(fields='url', **search_constraints):
    	        for url_encoded in result['url']:
    	            url, _, access_type = url_encoded.split('|')
    	            if access_type.lower().startswith(url_type):
		    	        
    	                result_url.append(url)		     		
    	
    	return result_url
	
if __name__ == "__main__":  # pragma nocover
    Command().run()
