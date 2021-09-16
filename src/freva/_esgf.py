from evaluation_system.commands.esgf import Command
import logging


__all__ = ['esgf']

def esgf(*args,dataset=False,query=False,show_facets=False,opendap=False,gridftp=False,**search_facets):





     return Command.search_esgf(*args, dataset=dataset,
                               show_facets=show_facets,
                               query=query,opendap=opendap,gridftp=gridftp,                    
                               **search_facets)
