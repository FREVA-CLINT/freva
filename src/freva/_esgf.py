

__all__ = ['esgf']

def esgf(*args,dataset=False
	  query=False,show_facets=False):





     return Command.search_esgf(*args, dataset=dataset,
                               show_facets=show_facets,
                               query=query,                    
                               **search_facets)
