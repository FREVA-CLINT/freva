"""Module to access the apache solr databrowser."""

from pathlib import Path

from evaluation_system.misc import logger
from evaluation_system.model.solr import SolrFindFiles

from typing import Any, Optional, Union, Dict, Iterator, List, overload, Literal

__all__ = ["databrowser"]


@overload
def databrowser(*, attributes: Literal[False], all_facets: Literal[False], facet: Union[str, List[str]]) -> Dict[Any, Dict[Any, Any]]:
    ...

@overload
def databrowser(*, attributes: Literal[False], all_facets: Literal[True]) -> Dict[Any, Dict[Any, Any]]:
    ...

@overload
def databrowser(*, attributes: Literal[True], all_facets: Literal[False], facet: Optional[Union[str, List[str]]]) -> Iterator[str]:
    ...


def databrowser(
    *,
    attributes: bool = False,
    all_facets: bool = False,
    facet: Optional[Union[str, List[str]]] = None,
    multiversion: bool = False,
    relevant_only: bool = False,
    batch_size: int = 10,
    count_facet_values: bool = False,
    **search_facets: Union[str, Path, int, List[str]],
) -> Union[Dict[Any, Dict[Any, Any]], Iterator[str]]:
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
    **search_facets:
        The searchfacets to be applied in the data search. If not given
        the whole dataset will be queried.
    multiversion:
        Select all versions and not just the latest version (default).
    relevant_only:
        Show only facets that filter more than one result.
    batch_size:
        Size of the search querey.
    count_facet_values:
        Show the number of files for each values in each facet.
    attributes:
        Retrieve all possible attributes for the current search
        instead of the files.
    all_facets:
        Retrieve all facets (attributes & values) instead of the files.
    facet:
        Retrieve these facets (attributes & values) instead of the files.


    Returns:
    --------
        collection : List, Dict of files, facets or attributes

    """
    facets: List[str] = []
    try:
        # If we don't convert a str to a str mypy will complain.
        f = Path(str(search_facets["file"]))
        search_facets["file"] = f'"\\{f.parent}/\\{f.name}"'
    except KeyError:
        pass
    if isinstance(facet, str):
        facet = [facet]
    facet = facet or []
    facets += [f for f in facet if f]
    latest = not multiversion
    if "version" in search_facets and latest:
        # it makes no sense to look for a specific version just among the latest
        # the speedup is marginal and it might not be what the user expects
        logger.warning("Turning latest off when searching for a specific version.")
        latest = False
    logger.debug("Searching dictionary: %s\n", search_facets)
    if (facets or all_facets) and not attributes:
        out = {}
        search_facets["facet.limit"] = search_facets.pop("facet_limit", -1)
        for att, values in SolrFindFiles.facets(
            facets=facets or None, latest_version=latest, **search_facets
        ).items():
            # values come in pairs: (value, count)
            value_count = len(values) // 2
            if relevant_only and value_count < 2:
                continue
            if count_facet_values:
                out[att] = {v: c for v, c in zip(*[iter(values)] * 2)}
            else:
                out[att] = values[::2]
        return out
    if attributes:
        # select all is none defined but this flag was set
        results = SolrFindFiles.facets(
            facets=facets or None, latest_version=latest, **search_facets
        )
        if relevant_only:
            return (k for k in results if len(results[k]) > 2)
        return (k for k in results)
    return SolrFindFiles.search(
        batch_size=batch_size, latest_version=latest, **search_facets
    )
