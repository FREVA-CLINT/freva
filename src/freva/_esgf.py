from evaluation_system.commands.esgf import Command
import logging


__all__ = ['esgf']

def esgf(datasets=False,query=False,show_facets=False,opendap=False,gridftp=False,download_script=False,**search_constraint):


	"""Find data in the ESGF.

	    

	import freva
	files = freva.esgf(model='MPI-ESM-LR', experiment='decadal2001', variable='tas', distrib='False')

	Parameters:
	-----------
	**search_constraint: str
	The search facets to be applied in the data search. 
	datasets            List the name of the datasets instead of showing the
				        urls.
	show-facet=FACET    <list> List all values for the given facet (might be
				        defined multiple times). The results show the possible
				        values of the selected facet according to the given
				        constraints and the number of *datasets* (not files)
				        that selecting such value as a constraint will result
				        (faceted search)
	opendap             List the name of the datasets instead of showing the
				        urls.
	gridftp             Show Opendap endpoints instead of the http default
				        ones (or skip them if none found)
	download_script=FILE
				        <file> Download wget_script for getting the files
				        instead of displaying anything (only http)
	query=QUERY         <list> Display results from <list> queried fields

	Returns:
	--------
	collection : List, Dict of files, facets or attributes

	"""


	return Command.search_esgf(datasets=datasets,show_facets=show_facets,query=query,opendap=opendap,gridftp=gridftp,download_script=download_script,**search_constraint)
