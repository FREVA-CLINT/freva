"""A Python module to access the apache solr databrowser."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional, Union, Iterator, overload
from typing_extensions import Literal

import lazy_import
from evaluation_system.misc import logger

SolrFindFiles = lazy_import.lazy_class("evaluation_system.model.solr.SolrFindFiles")

__all__ = ["databrowser"]


@overload
def databrowser(
    *,
    count: Literal[True],
    all_facets: Literal[False],
    facet: Literal[None],
) -> int:
    ...


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
    count: Literal[False],
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
    batch_size: int = 5000,
    count: bool = False,
    time: str = "",
    time_select: str = "flexible",
    **search_facets: Union[str, Path, int, list[str]],
) -> Union[dict[Any, dict[Any, Any]], Iterator[str], int]:
    """Find data in the system.

    You can either search for files or data facets (variable, model, ...)
    that are available. The query is of the form key=value. <value> might
    use *, ? as wildcards or any regular expression.

    Parameters
    ----------
    **search_facets: Union[str, Path, in, list[str]]
        The facets to be applied in the data search. If not given
        the whole dataset will be queried.
    time: str
        Special search facet to refine/subset search results by time.
        This can be a string representation of a time range or a single
        time step. The time steps have to follow ISO-8601. Valid strings are
        ``%Y-%m-%dT%H:%M`` to ``%Y-%m-%dT%H:%M`` for time ranges and
        ``%Y-%m-%dT%H:%M``. **Note**: You don't have to give the full string
        format to subset time steps ``%Y``, ``%Y-%m`` etc are also valid.
    time_select: str, default: flexible
        Operator that specifies how the time period is selected. Choose from
        flexible (default), strict or file. ``strict`` returns only those files
        that have the *entire* time period covered. The time search ``2000 to
        2012`` will not select files containing data from 2010 to 2020 with
        the ``strict`` method. ``flexible`` will select those files as
        ``flexible`` returns those files that have either start or end period
        covered. ``file`` will only return files where the entire time
        period is contained within *one single* file.
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
    count: bool, default: False
        Display only this amount for search results.

    Returns
    -------
    Iterator :
        If ``all_facets`` is False and ``facet`` is None an
        iterator with results.
    int :
        If ``all_facets`` is False and ``facet`` is None and ``count`` is True
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

    Search for files between a two given time steps:

    .. execute_code::

        import freva
        file_range = freva.databrowser(project="obs*", time="2016-09-02T22:15 to 2016-10")
        for file in file_range:
            print(file)

    The default method for selecting time periods is ``flexible``, which means
    all files are selected that cover at least start or end date. The
    ``strict`` method implies that the *entire* search time period has to be
    covered by the files. Using the ``strict`` method in the example above would
    only yield one file because the first file contains time steps prior to the
    start of the time period:

    .. execute_code::

        import freva
        file_range = freva.databrowser(project="obs*", time="2016-09-02T22:15 to 2016-10", time_select="strict")
        for file in file_range:
            print(file)


    Search for facets in the system:

    .. execute_code::

        import freva
        all_facets = freva.databrowser(project='obs*', all_facets=True)
        print(all_facets)
        spec_facets = freva.databrowser(project='obs*',
                                        facet=["time_frequency", "variable"])
        print(spec_facets)

    Get all models that have a given time step:

    .. execute_code::

        import freva
        model = list(freva.databrowser(project="obs*", time="2016-09-02T22:10"))
        print(model)

    Reverse search: retrieving meta data from a known file

    .. execute_code::

        import freva
        from pathlib import Path
        file = ".docker/data/observations/grid/CPC/CPC/cmorph/30min/atmos/30min/r1i1p1/v20210618/pr/pr_30min_CPC_cmorph_r1i1p1_201609020000-201609020030.nc"
        res = freva.databrowser(file=file, all_facets=True)
        print(res)

    Check the number of files in the system

    .. execute_code::

        import freva
        num_files = freva.databrowser(experiment="cmorph", count=True)
        print(num_files)

    """
    select_methods: dict[str, str] = {
        "strict": "Within",
        "flexible": "Intersects",
        "file": "Contains",
    }
    facets: list[str] = []
    try:
        search_facets["time_select"] = select_methods[time_select]
    except KeyError as error:
        methods = ", ".join(select_methods.keys())
        raise ValueError(f"Time select method has one of {methods}")
    search_facets["time"] = time
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
    core = {True: "latest", False: "files"}[latest]
    logger.debug("Searching dictionary: %s\n", search_facets)
    solr_core = SolrFindFiles(core=core)
    if (facets or all_facets) and not attributes:
        out = {}
        search_facets["facet.limit"] = search_facets.pop("facet_limit", -1)
        for att, values in solr_core._facets(
            facets=facets or None, latest_version=False, **search_facets
        ).items():
            # values come in pairs: (value, count)
            value_count = len(values) // 2
            if relevant_only and value_count < 2:
                continue
            if count:
                out[att] = {v: c for v, c in zip(*[iter(values)] * 2)}
            else:
                out[att] = values[::2]
        return out
    if attributes:
        # select all is none defined but this flag was set
        results = solr_core._facets(
            facets=facets or None, latest_version=False, **search_facets
        )
        if relevant_only:
            return (k for k in results if len(results[k]) > 2)
        return (k for k in results)
    if count:
        return solr_core._retrieve_metadata(**search_facets).num_objects
    search_results = solr_core._search(
        batch_size=batch_size,
        latest_version=latest,
        **search_facets,
    )
    return search_results
