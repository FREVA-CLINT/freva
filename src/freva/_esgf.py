"""Module to access the esgf data catalogue."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, overload

import lazy_import
from typing_extensions import Literal

from .utils import handled_exception

P2P = lazy_import.lazy_class("evaluation_system.model.esgf.P2P")


__all__ = [
    "esgf_browser",
    "esgf_facets",
    "esgf_datasets",
    "esgf_download",
    "esgf_query",
]


@handled_exception
def esgf_browser(
    opendap: bool = False,
    gridftp: bool = False,
    **search_constraints: dict[str, str],
) -> list[str]:
    """Find data in the ESGF.

    The method queries the ESGF nodes for file URLs (default) or
    opendap/gridftp endpoints as well.

    The ``key=value`` syntax follows that of ``freva.databrowser``
    but the key names follow the ESGF standards for each dataset.
    Search of multiple values for the same key can be achieved
    either as a ``str`` concatenation (e.g.``frequency="3hr,mon" ``
    with **no** space between variables) or as a ``list``
    (e.g. ``frequency=["3hr", "mon"]``).

    Parameters:
    -----------
    opendap: bool, default: False
        List opendap endpoints instead of http ones.
    gridftp: bool, default: False
        Show gridftp endpoints instead of the http default
        ones (or skip them if none found)
    **search_constraints: Union[str, Path, in, list[str]]
        Search facets to be applied in the data search.

    Returns:
    --------
    list :
        Collection of files

    Example
    -------

    Similarly to ``freva.databrowser``, ``freva.esgf_browser``
    expects a list of ``key=value`` pairs in no particular
    order, but unlike the former it *is* case sensitive.

    Given that your Freva instance is configured at DKRZ,
    if we want to search the URLs of all the files stored
    at the (DKRZ) local node (``distrib=false``) holding
    the latest version (``latest=true``) of the variable
    uas (``variable=uas``) for either 3hr or monthly
    time frequencies ( ``frequency=["3hr", "mon"]``)
    and for a particular realization within the
    project ``CMIP6``:

    .. execute_code::

        import freva
        files = freva.esgf_browser(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            frequency="3hr,mon",
            variable="uas",
            variant_label="r1i1p1f2",
            distrib=False,
            latest=True,
        )
        print(f"{len(files) =}")
        for file in files[:5]:
            print(file)

    In order to list the opendap endpoints (``opendap=True``):

    .. execute_code::

        import freva
        opendap = freva.esgf_browser(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            frequency="3hr",
            variable="uas",
            variant_label="r1i1p1f2",
            distrib=False,
            latest=True,
            opendap=True,
        )
        print(opendap)

    Or the gridftp endpoints instead (``gridftp=True``):

    .. execute_code::
        :hide_code:

        import freva
        gridftp = freva.esgf_browser(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            frequency="3hr",
            variable="uas",
            variant_label="r1i1p1f2",
            distrib=False,
            latest=True,
            gridftp=True,
        )
        print(gridftp)
    """
    result_url = []
    url_type = "http"
    if opendap:
        url_type = "opendap"
    if gridftp:
        url_type = "gridftp"
    p2p = P2P()
    for result in p2p.files(fields="url", **search_constraints):
        for url_encoded in result["url"]:
            url, _, access_type = url_encoded.split("|")
            if access_type.lower().startswith(url_type):
                result_url.append(url)
    return result_url


@handled_exception
def esgf_facets(
    show_facet: Optional[Union[str, list[str]]] = None,
    **search_constraints: dict[str, str],
) -> dict[str, list[str]]:
    """Search for data attributes (facets) through ESGF.

    The method queries the ESGF nodes for available search facets (keys)
    like model, experiment etc. The ``key=value`` syntax follows that of
    ``freva.facet_search`` but the key names follow the ESGF standards
    for each dataset.

    Parameters:
    -----------
    show_facet: Union[str, list[str]], default: None
        List all values for the given facet (might be
        defined multiple times). The results show the possible
        values of the selected facet according to the given
        constraints and the number of *datasets* (not files)
        that selecting such value as a constraint will result
        (faceted search)
    **search_constraints: Union[str, Path, in, list[str]]
        Search facets to be applied in the data search.

    Returns:
    --------
    dict[str, list[str]]:
        Collection of facets

    Example
    -------

    List the values of the attributes ``variable``
    and ``time_frequency`` stored at the (DKRZ) local node
    (``distrib=false``) holding the latest version (``latest=true``)
    for a particular realization within the project ``CMIP6``:

    .. execute_code::

        import freva
        facets = freva.esgf_facets(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            distrib=False,
            latest=True,
            show_facet=["variable", "frequency"])
        print(facets)

    """
    show_facet = show_facet or []
    p2p = P2P()
    return p2p.get_facets(show_facet, **search_constraints)


@handled_exception
def esgf_datasets(
    **search_constraints: dict[str, str],
) -> list[tuple[str, str]]:
    """List the name of the datasets (and version) in the ESGF.

    The method queries the ESGF nodes for dataset information.
    The ``key=value`` syntax follows that of ``freva.databrowser``
    but the key names follow the ESGF standards for each dataset.

    Parameters:
    -----------
    **search_constraints: Union[str, Path, in, list[str]]
        Search facets to be applied in the data search.

    Returns:
    --------
    list[tuple[str, str]]:
        list of (dataset_name, version_number) tuples

    Example
    -------

    List the datasets corresponding to a query of files
    stored at the (DKRZ) local node (``distrib=false``)
    holding the latest version (``latest=true``) for a particular
    realization within the project ``CMIP6``:

    .. execute_code::

        import freva
        datasets = freva.esgf_datasets(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            frequency="3hr",
            variable="uas",
            variant_label="r1i1p1f2",
            distrib=False,
            latest=True,
            )
        print(f"{len(datasets) =}")
        for dataset in datasets[:5]:
            print(dataset)
    """
    p2p = P2P()
    return sorted(p2p.get_datasets_names(**search_constraints))


@handled_exception
def esgf_download(
    download_script: Optional[Union[str, Path]] = None,
    **search_constraints: dict[str, str],
) -> Union[str, Path]:
    """Create a script file to download the queried files at ESGF.

    The method creates a bash script wrapper of a wget query
    from ESGF dataset(s) (only http).

    Parameters:
    -----------
    download_script: Union[str, Path], default: None
        Download wget_script for getting the files
        instead of displaying anything (only http)
    **search_constraints: Union[str, Path, in, list[str]]
        Search facets to be applied in the data search.

    Returns:
    --------
    Union[str, Path]:
        wget_script to download the files (only http).

    Example
    -------

    Create a wget script to download the queried URLs:

    .. execute_code::

        import freva
        freva.esgf_download(project="CMIP5",
                    experiment="decadal1960",
                    variable="tas", distrib=False, latest=True,
                    download_script="/tmp/script.get")

        with open('/tmp/script.get', 'r') as f:
            content = f.readlines()
            print(" ".join(content[:10]))

    .. note::

        You will need an OpenID account to download the data,
        for example `here <https://esgf-data.dkrz.de/user/add/?next=http://esgf-data.dkrz.de/projects/esgf-dkrz/>`_.

        There is a `ESGF PyClient <https://esgf-pyclient.readthedocs.io/en/latest/index.html>`_ as well.


    """
    p2p = P2P()
    if not download_script:
        import random
        import string

        random_string = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )
        base_path = "/tmp/script"
        extension = "get"
        download_script = f"{base_path}-{random_string}.{extension}"
    download_script = Path(download_script)
    download_script.touch(0o755)
    with download_script.open("bw") as f:
        f.write(p2p.get_wget(**search_constraints))
    return str(f"Download script successfully saved to {download_script}")


@handled_exception
def esgf_query(
    query: Optional[Union[str, list[str]]] = None,
    **search_constraints: dict[str, str],
) -> list[dict[str, list[str]]]:
    """Query fields from ESGF and group them per dataset

    The method queries fields (e.g. facets) and groups them by dataset
    in a list of dictionaries.

    Parameters:
    -----------
    query:
        Display results from <list> queried fields
    **search_constraints:
        Search facets to be applied in the data search.

    Returns:
    --------
    list[dict[str, list[str]]]:
        List of dictionaries with the queried elements for each dataset

    Example:
    --------

    Show the ``key=value`` pair of selected elements for a search (e.g.
    ``query=["url","master_id","distribution","mip_era","activity_id","source_id","variable","product","version"]``):

    .. execute_code::

        import json, freva
        queries = freva.esgf_query(
            mip_era="CMIP6",
            activity_id="ScenarioMIP",
            source_id="CNRM-CM6-1",
            institution_id="CNRM-CERFACS",
            experiment_id="ssp585",
            frequency="3hr",
            variant_label="r1i1p1f2",
            distrib=False,
            latest=True,
            query=["url","master_id","distribution",
                "mip_era","activity_id","source_id",
                "variable","product","version"],
        )
        print(json.dumps(queries[:2], indent=3))
    """
    p2p = P2P()
    if isinstance(query, list):
        query = ",".join(query)
    return p2p.get_datasets(fields=query, **search_constraints)
