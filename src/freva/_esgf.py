from evaluation_system.commands.esgf import Command
import logging


__all__ = ['esgf']

def esgf(dataset=False,query=False,show_facets=False,opendap=False,gridftp=False,download_script=False,**search_constraint):





     return Command.search_esgf(dataset=dataset,
                               show_facets=show_facets,
                               query=query,opendap=opendap,gridftp=gridftp,download_script=download_script,                   
                               **search_constraint)
