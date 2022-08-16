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

    ::
        import freva
        files = freva.esgf(model='MPI-ESM-LR',
                           experiment='decadal2001',
                           variable='tas'
                )

    Parameters:
    -----------
    datasets:
        List the name of the datasets instead of showing the urls.
    show_facet:
        List all values for the given facet (might be
        defined multiple times). The results show the possible
        values of the selected facet according to the given
        constraints and the number of *datasets* (not files)
        that selecting such value as a constraint will result
        (faceted search)
    opendap:
        List the name of the datasets instead of showing the urls.
    gridftp:
        Show Opendap endpoints instead of the http default
        ones (or skip them if none found)
    download_script:
        Download wget_script for getting the files
        instead of displaying anything (only http)
    query:
        Display results from <list> queried fields
    **search_constraints:
        Search facets to be applied in the data search.

    Returns:
    --------
    Collection of files, facets or attributes

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
            # we get multiple fields queried, return in a tructured fashion
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
