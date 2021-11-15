from warnings import warn

from evaluation_system.commands.databrowser import Command
from evaluation_system.model.solr import SolrFindFiles
import logging

__all__ = ['databrowser']

def databrowser(*,multiversion=False,
                relevant_only=False,
                batch_size=10,
                count_facet_values=False,
                attributes=False,
                all_facets=False,
                facet=None,
                **search_facets):
    """Find data in the system.

    The query is of the form key=value. <value> might use *, ? as wildcards or 
    any regular expression.

    ::

        import freva
        files = freva.databrowser(project='baseline1', model='MPI-ESM-LR',
                                  experiment='decadal200[0-3]',
                                  time_frequency='*hr',
                                  variable='ta|tas|vu')

    Parameters:
    -----------
    **search_facets: str
        The search facets to be applied in the data search. If not given
        the whole dataset will be queried.
    multiversion: bool (default False)
        Select all versions and not just the latest version (default).
    relevant_only: bool (default False)
        Show only facets that filter more than one result.
    batch_size: int (default 10)
        Size of the search querey.
    count_facet_values: bool (default False)
        Show the number of files for each values in each facet.
    attributes: bool (default False)
        Retrieve all possible attributes for the current search
        instead of the files.
    all_facets: bool (default False)
        Retrieve all facets (attributes & values) instead of the files.
    facet: str (default None)
        Retrieve these facets (attributes & values) instead of the files.


    Returns:
    --------
        collection : List, Dict of files, facets or attributes

    """
    return Command.search_data(multiversion=multiversion,
                               relevant_only=relevant_only,
                               batch_size=batch_size,
                               count_facet_values=count_facet_values,
                               attributes=attributes,
                               all_facets=all_facets,
                               facet=facet,
                               **search_facets)
