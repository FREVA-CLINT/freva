"""Module to access the esgf data catalogue."""
from __future__ import annotations
from pathlib import Path
from typing import Union, Optional, overload
from typing_extensions import Literal

import lazy_import


P2P = lazy_import.lazy_class("evaluation_system.model.esgf.P2P")


__all__ = ["esgf"]


@overload
def esgf(datasets: Literal[True]) -> list[tuple[str, str]]:
    ...


@overload
def esgf(datasets: Literal[False], show_facet: str) -> dict[str, list[str]]:
    ...


def esgf(
    datasets: bool = False,
    show_facet: Optional[Union[str, list[str]]] = None,
    download_script: Optional[Union[str, Path]] = None,
    query: Optional[str] = None,
    opendap: bool = False,
    gridftp: bool = False,
    **search_constraints: dict[str, str],
) -> Union[str, list[tuple[str, str]], dict[str, list[str]]]:
    """Find data in the ESGF.

    The method queries the ESGF nodes for file URLs, facet
    information, or dataset/opendap/gridftp information.
    It can also create a bash script wrapper of a wget query.
    The key=value syntax follows that of ``freva.databrowser`` 
    but the key names follow the ESGF standards for each dataset.

    Parameters:
    -----------
    datasets: bool, default: False
        List the name of the datasets instead of showing the urls.
    show_facet: Union[str, list[str]], default: None
        List all values for the given facet (might be
        defined multiple times). The results show the possible
        values of the selected facet according to the given
        constraints and the number of *datasets* (not files)
        that selecting such value as a constraint will result
        (faceted search)
    opendap: bool, default: False
        List opendap endpoints instead of http ones.
    gridftp: bool, default: False
        Show gridftp endpoints instead of the http default
        ones (or skip them if none found)
    download_script: Union[str, Path], default: None
        Download wget_script for getting the files
        instead of displaying anything (only http)
    query: str, default: None
        Display results from <list> queried fields
    **search_constraints: Union[str, Path, in, list[str]]
        Search facets to be applied in the data search.

    Returns:
    --------
    list :
        Collection of files, facets or attributes

    Example
    -------

    Similarly to ``freva.databrowser``, ``freva.esgf`` expects 
    a list of ``key=value`` pairs in no particular order, 
    but unlike the former it *is* case sensitive.
    
    Given that your Freva instance is configured at DKRZ,
    if we want to search the URLs of all the files stored
    at the (DKRZ) local node (``distrib=false``) holding the latest version
    (``latest=true``) of the variable tas (``variable=tas``) for the
    experiment ``decadal1960`` and project ``CMIP5`` 
    (these all are search facets from the API):

    .. execute_code::

        import freva
        files = freva.esgf(project="CMIP5", 
                           experiment="decadal1960", 
                           variable="tas", distrib=False, latest=True)
        print(len(files))
        for file in files[:5]:
            print(file)

    
    Show the values of the attributes ``variable`` and ``time_frequency``:

    .. execute_code::

        import freva
        facets = freva.esgf(project="CMIP5", distrib=False, latest=True,
                           show_facet=["variable", "time_frequency"])
        print(facets)
            
    
    List the name of the datasets instead:

    .. execute_code::

        import freva
        datasets = freva.esgf(project="CMIP5", 
                           experiment="decadal1960", 
                           variable="tas", distrib=False, latest=True,
                           datasets=True)
        print(len(datasets))
        for dataset in datasets[:5]:
            print(dataset)

    List the opendap endpoints:

    .. execute_code::

        import freva
        opendap = freva.esgf(
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
        
    Or the gridftp endpoints instead:

    .. execute_code::
        :hide_code:

        import freva
        gridftp = freva.esgf(
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

    Create a wget script to download the queried URLs:

    .. execute_code::

        import freva
        freva.esgf(project="CMIP5", 
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

    result_url = []
    show_facet = show_facet or []
    url_type = "http"
    if opendap:
        url_type = "opendap"
    if gridftp:
        url_type = "gridftp"
    # find the files and display them
    p2p = P2P()
    if download_script:
        download_script = Path(download_script)
        download_script.touch(0o755)
        with download_script.open("bw") as f:
            f.write(p2p.get_wget(**search_constraints))
        return str(
            f"Download script successfully saved to {download_script}"
        )  # there's nothing more to be executed after this
    if datasets:
        return sorted(p2p.get_datasets_names(**search_constraints))
    if isinstance(query, str):
        if len(query.split(",")) > 1:
            # we get multiple fields queried, return in a structured fashion
            return p2p.show(
                p2p.get_datasets(fields=query, **search_constraints), return_str=True
            )
        else:
            # if only one then return directly
            return p2p.get_datasets(fields=query, **search_constraints)
    if show_facet:
        return p2p.get_facets(show_facet, **search_constraints)
    for result in p2p.files(fields="url", **search_constraints):
        for url_encoded in result["url"]:
            url, _, access_type = url_encoded.split("|")
            if access_type.lower().startswith(url_type):
                result_url.append(url)
    return result_url
