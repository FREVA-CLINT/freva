"""A Python module to access the apache solr databrowser."""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Iterator, Optional, Union, overload

import lazy_import
from typing_extensions import Literal

from evaluation_system.misc import logger

from .utils import handled_exception

SolrFindFiles = lazy_import.lazy_class("evaluation_system.model.solr.SolrFindFiles")


__all__ = ["databrowser", "search_facets", "count_values"]


def _proc_search_facets(
    time_select: Literal["flexible", "strict", "file"] = "flexible",
    **search_facets: str | list[str] | int,
) -> dict[str, str | list[str] | int]:
    """Correct the facet values if needed."""
    select_methods: dict[str, str] = {
        "strict": "Within",
        "flexible": "Intersects",
        "file": "Contains",
    }
    try:
        search_facets["time_select"] = select_methods[time_select]
    except KeyError as error:
        methods = ", ".join(select_methods.keys())
        raise ValueError(f"Time select method has one of {methods}") from error
    search_facets["time"] = search_facets.get("time", "")
    for key in ("file", "uri"):
        try:
            search_facets[key] = json.dumps(search_facets[key])
        except KeyError:
            pass
    return search_facets


@overload
def count_values(
    *,
    facet: Union[str, list[str]],
    time: str = "",
    time_select: Literal["strict", "flexible", "file"] = "flexible",
    multiversion: bool = False,
    **search_facets: str | list[str] | int,
) -> dict[str, dict[str, int]]:
    ...


@overload
def count_values(
    *,
    facet: Literal[None],
    time: str = "",
    time_select: Literal["strict", "flexible", "file"] = "flexible",
    multiversion: bool = False,
    **search_facets: str | list[str] | int,
) -> int:
    ...


@handled_exception
def count_values(
    *,
    time: str = "",
    time_select: Literal["strict", "flexible", "file"] = "flexible",
    multiversion: bool = False,
    facet: str | list[str] | None = None,
    **search_facets: str | list[str] | int,
) -> int | dict[str, dict[str, int]]:
    """Count the number of found objects in the databrowser.

    Parameters
    ----------
    time: str, default: ""
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
    multiversion: bool, default: False
        Select all versions and not just the latest version (default).
    facet: Union[str, list[str]], default: None
        Count these these facets (attributes & values) instead of the number
        of total files. If None (default), the number of total files will
        be returned.
    **search_facets: str
        The facets to be applied in the data search. If not given
        the whole dataset will be queried.

    Returns
    -------
    int, dict[str, int]:
        Number of found objects, if the *facet* key is/are given then the
        a dictionary with the number of objects for each search facet/key
        is given.

    Example
    -------
    .. execute_code::

        import freva
        num_files = freva.count_values(experiment="cmorph")
        print(num_files)

    .. execute_code::

        import freva
        print(freva.count_values(facet="*"))

    """
    search_facets = _proc_search_facets(
        time_select=time_select, time=time, **search_facets
    )
    count_all = facet is None
    if isinstance(facet, str):
        facet = [facet]
    if facet in (["*"], ["all"]):
        facet = []
    facet = facet or []
    latest = not multiversion
    if "version" in search_facets and latest:
        # it makes no sense to look for a specific version just among the latest
        # the speedup is marginal and it might not be what the user expects
        logger.warning("Turning latest off when searching for a specific version.")
        latest = False
    core = {True: "latest", False: "files"}[latest]
    logger.debug("Searching dictionary: %s\n", search_facets)
    search_facets["facet.limit"] = search_facets.pop("facet_limit", -1)
    if count_all:
        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", category=PendingDeprecationWarning)
            return (
                SolrFindFiles(core=core)._retrieve_metadata(**search_facets).num_objects
            )
    with warnings.catch_warnings():
        warnings.filterwarnings(action="ignore", category=PendingDeprecationWarning)
        results = SolrFindFiles(core=core)._facets(facet or None, **search_facets)
    out: dict[str, dict[str, int]] = {}
    for att in facet or results.keys():
        values = results[att]
        out[att] = {str(v): int(c) for v, c in zip(*[iter(values)] * 2)}
    return out


@handled_exception
def facet_search(
    *,
    time: str = "",
    time_select: Literal["strict", "flexible", "file"] = "flexible",
    multiversion: bool = False,
    facet: str | list[str] | None = None,
    **search_facets: str | list[str] | int,
) -> dict[str, list[str]]:
    """Search for data attributes (factes) in the databrowser.

    The method queries the databrowser for available search facets (keys)
    like model, experiment etc.

    Parameters
    ----------
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
    facet: Union[str, list[str]], default: None
        Retrieve information about these facets (attributes & values).
        If None given (default), information about all available facets is
        returned.
    multiversion: bool, default: False
        Select all versions and not just the latest version (default).
    **search_facets: str
        The facets to be applied in the data search. If not given
        the whole dataset will be queried.

    Returns
    -------
    dict[str, list[str]]:
        Dictionary with a list search facet values for each search facet key


    Example
    -------

    .. execute_code::

        import freva
        all_facets = freva.facet_search(project='obs*')
        print(all_facets)
        spec_facets = freva.facet_search(project='obs*',
                                         facet=["time_frequency", "variable"])
        print(spec_facets)

    Get all models that have a given time step:

    .. execute_code::

        import freva
        model = list(freva.facet_search(project="obs*", time="2016-09-02T22:10"))
        print(model)

    Reverse search: retrieving meta data from a known file

    .. execute_code::

        import freva
        from pathlib import Path
        file = ".docker/data/observations/grid/CPC/CPC/cmorph/30min/atmos/30min/r1i1p1/v20210618/pr/pr_30min_CPC_cmorph_r1i1p1_201609020000-201609020030.nc"
        res = freva.facet_search(file=str(Path(file).absolute()))
        print(res)

    """
    search_facets = _proc_search_facets(
        time_select=time_select, time=time, **search_facets
    )
    if isinstance(facet, str):
        facet = [facet]
    if facet in (["*"], ["all"]):
        facet = []
    facet = facet or []
    latest = not multiversion
    if "version" in search_facets and latest:
        # it makes no sense to look for a specific version just among the latest
        # the speedup is marginal and it might not be what the user expects
        logger.warning("Turning latest off when searching for a specific version.")
        latest = False
    core = {True: "latest", False: "files"}[latest]
    logger.debug("Searching dictionary: %s\n", search_facets)
    search_facets["facet.limit"] = search_facets.pop("facet_limit", -1)
    with warnings.catch_warnings():
        warnings.filterwarnings(action="ignore", category=PendingDeprecationWarning)
        results = SolrFindFiles(core=core)._facets(
            facets=facet or None, latest_version=False, **search_facets
        )
    return {f: v[::2] for f, v in results.items()}


@handled_exception
def databrowser(
    *,
    multiversion: bool = False,
    batch_size: int = 5000,
    uniq_key: Literal["file", "uri"] = "file",
    time: str = "",
    time_select: Literal["flexible", "strict", "file"] = "flexible",
    **search_facets: Union[str, list[str], int],
) -> Union[dict[str, dict[str, int]], dict[str, list[str]], Iterator[str], int]:
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
    uniq_key: str, default: file
        Chose if the solr search query should return paths to files or
        uris, uris will have the file path along with protocol of the storage
        system. Uris can be useful if the the search query result should be
        used libraries like fsspec.
    multiversion: bool, default: False
        Select all versions and not just the latest version (default).
    batch_size: int, default: 5000
        Size of the search querey.

    Returns
    -------
    Iterator :
        If ``all_facets`` is False and ``facet`` is None an
        iterator with results.


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
    """
    core = {True: "latest", False: "files"}[not multiversion]
    search_facets = _proc_search_facets(
        time_select=time_select, time=time, **search_facets
    )
    with warnings.catch_warnings():
        warnings.filterwarnings(action="ignore", category=PendingDeprecationWarning)
        search_results = SolrFindFiles(core=core)._search(
            batch_size=batch_size,
            latest_version=not multiversion,
            uniq_key=uniq_key,
            **search_facets,
        )
    return search_results
