"""A Python module to access the apache solr databrowser."""
from __future__ import annotations
from pathlib import Path

from evaluation_system.misc import logger
from evaluation_system.model.solr import SolrFindFiles

from typing import Any, Optional, Union, Iterator, overload
from typing_extensions import Literal

__all__ = ["databrowser"]


@overload
def databrowser(
    *,
    attributes: Literal[False],
    facet: Union[str, list[str]],
) -> dict[Any, dict[str, Any]]:
    ...


@overload
def databrowser(
    *,
    all_facets: Literal[False],
    facet: Literal[None],
) -> Iterator[str]:
    ...


def databrowser(
    *,
    attributes: bool = False,
    all_facets: bool = False,
    facet: Optional[Union[str, list[str]]] = None,
    multiversion: bool = False,
    relevant_only: bool = False,
    batch_size: int = 10,
    count_facet_values: bool = False,
    **search_facets: Union[str, Path, int, list[str]],
) -> Union[dict[Any, dict[Any, Any]], Iterator[str]]:
    """Find data in the system.

    You can either search for files or data facets (variable, model, ...)
    that are available. The query is of the form key=value. <value> might
    use *, ? as wildcards or any regular expression.

    Parameters
    ----------
    **search_facets: Union[str, Path, in, list[str]]
        The facets to be applied in the data search. If not given
        the whole dataset will be queried.
    all_facets: bool, default: False
        Retrieve all facets (attributes & values) instead of the files.
    facet: Union[str, list[str]], default: None
        Retrieve these facets (attributes & values) instead of the files.
    attributes: bool, default: False
        Retrieve all possible attributes for the current search
        instead of the files.
    multiversion: bool, default: False
        Select all versions and not just the latest version (default).
    relevant_only: bool, default: False
        Show only facets that filter more than one result.
    batch_size: int, default: 10
        Size of the search querey.
    count_facet_values: bool, default: False
        Display only this amount for search results.

    Returns
    -------
    Iterator :
        If ``all_facets`` is False and ``facet`` is None an
        iterator with results.
    dict[Any, dict[str, Any] :
        dictionary for facet results, if ``all_facets`` is True or ``facet``
        was given a value (str or list[str])


    Example
    -------

    Seach for files in the system:

    .. execute_code::

        import freva
        files = freva.databrowser(project='obs*', institute='cpc',
                                  time_frequency='??min',
                                  variable='pr')
        print(files)
        print(next(files))
        for file in files:
            print(file)
            break
        facets = freva.databrowser(project='obs*', attributes=True)
        print(list(facets))


    Search for facets in the system:

    .. execute_code::

        import freva
        all_facets = freva.databrowser(project='obs*', all_facets=True)
        print(all_facets)
        spec_facets = freva.databrowser(project='obs*',
                                        facet=["time_frequency", "variable"])
        print(spec_facets)

    Reverse search: retrieving meta data from a knwon file

    .. execute_code::

        import freva
        from pathlib import Path
        file = ".docker/data/observations/grid/CPC/CPC/cmorph/30min/atmos/30min/r1i1p1/v20210618/pr/pr_30min_CPC_cmorph_r1i1p1_201609020000-201609020030.nc"
        res = freva.databrowser(file=file, all_facets=True)
        print(res)

    """
    facets: list[str] = []
    try:
        # If we don't convert a str to a str mypy will complain.
        f = Path(str(search_facets["file"])).expanduser().absolute()
        search_facets["file"] = f'"\{f}"'
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
