"""
Created on 11.03.2013

@author: Sebastian Illing / estani

This package encapsulate access to a solr instance
"""

from __future__ import annotations
import urllib
from typing import cast, Union, List, NamedTuple

from evaluation_system.model.solr_core import SolrCore
from evaluation_system.misc import logger, utils

SolrResponse = NamedTuple(
    "SolrResponse",
    [("num_objects", int), ("start", int), ("exact", bool), ("docs", List[str])],
)


class SolrFindFiles(object):
    """Encapsulate access to Solr like the find files command"""

    def __init__(self, core=None, host=None, port=None, get_status=False):
        """Create the connection pointing to the proper solr url and core.
        The default values of these parameters are setup in evaluation_system.model.solr_core.SolrCore
        and read from the configuration file.

        :param core: name of the solr core that will be used.
        :param host: hostname of the machine where the solr core is to be found.
        :param port: port number of the machine where the solr core is to be found.
        :param get_status: if the core should be contacted in an attempt to get more metadata."""
        self.solr = SolrCore(core, host=host, port=port, get_status=get_status)

    def __str__(self):  # pragma: no cover
        return "<SolrFindFiles %s>" % self.solr

    def _to_solr_query(self, partial_dict: dict[str, Union[str, list[str]]]) -> str:
        """Creates a Solr query assuming the default operator is "AND". See schema.xml for that."""
        params = []
        partial_dict = self._add_time_query(partial_dict)
        # these are special Solr keys that we might get and we assume are not meant for the search
        special_keys = ("q", "fl", "fq", "facet.limit", "sort")
        logger.debug(partial_dict)
        for key, value in partial_dict.items():
            if key in special_keys:
                params.append((key, value))
            else:
                if key.endswith("_not_"):
                    # handle negation
                    key = "-" + key[:-5]
                if isinstance(value, list):
                    # implies an or
                    constraint = " OR ".join(["%s:%s" % (key, v) for v in value])
                else:
                    constraint = "%s:%s" % (key, value)
                params.append(
                    (
                        "fq",
                        constraint,
                    )
                )
        logger.debug(params)
        return urllib.parse.urlencode(params)

    def _get_file_query_parameters(self, **search_dict: Union[str, list[str]]) -> str:

        partial_dict = search_dict.copy()
        for key in ("start", "row"):
            _ = partial_dict.pop("start", None)
        for key, value in {"q": "*:*", "fl": "file", "sort": "file desc"}.items():
            partial_dict.setdefault(key, value)
        if "text" in partial_dict:
            partial_dict["q"] = partial_dict.pop("text")
        return self._to_solr_query(partial_dict)

    def _retrieve_metadata(self, **search_dict: str) -> SolrResponse:
        """Retrieve metadata from databrowser.

        Parameters
        ----------

        **search_dict: str
            Search query parameter

        Returns
        -------
        evaluation_system.model.solr.SolrResponse:
          NamedTuple of metadata on the search query results.
        """
        query = self._get_file_query_parameters(**search_dict)
        anw = self.solr.get_json("select?facet=true&rows=0&%s" % query)["response"]
        return SolrResponse(
            num_objects=anw["numFound"],
            start=anw["start"],
            exact=anw["numFoundExact"],
            docs=anw["docs"],
        )

    def _search(
        self,
        batch_size=10000,
        latest_version=False,
        rows=None,
        **partial_dict,
    ):
        """This encapsulates the Solr call to get documents and returns an iterator providing the. The special
        parameter _retrieve_metadata will affect the first value returned by the iterator.

        :param batch_size: the amount of files to be buffered from Solr.
        :param latest_version: if the search should *try* to find the latest version from all contained here. Please note
         that we don't use this anymore. Instead we have 2 cores and this is defined directly in :class:`SolrFindFiles.search`.
         It was changed because it was slow and required too much memory.
        known beforehand how many values are going to be returned, even before getting them all. To avoid this we might
        implement a result set object. But that would break the find_files compatibility."""
        offset = int(partial_dict.pop("start", "0"))
        query = self._get_file_query_parameters(**partial_dict)
        metadata = self._retrieve_metadata(**partial_dict)
        if rows:
            results_to_visit = min(metadata.num_objects, rows)
        else:
            results_to_visit = metadata.num_objects
        while results_to_visit > 0:
            batch_size = min(batch_size, results_to_visit)
            answer = self.solr.get_json(
                "select?start=%s&rows=%s&%s" % (offset, batch_size, query)
            )
            offset = answer["response"]["start"]
            iter_answer = answer["response"]["docs"]
            for item in iter_answer:
                yield item["file"]
                results_to_visit -= 1
            offset += batch_size

    @staticmethod
    def _add_time_query(
        search_dict: dict[str, Union[str, list[str]]]
    ) -> dict[str, Union[list[str], str]]:
        """Add a potential time query string to the search dict."""
        time_subset = cast(str, search_dict.pop("time", ""))
        operator = cast(str, search_dict.pop("time_select", ""))
        if time_subset:
            start, _, end = time_subset.lower().partition("to")
            start = utils.convert_str_to_timestamp(start.strip() or "0", "")
            end = utils.convert_str_to_timestamp(end.strip() or start, "")
            if not start or not end:
                raise ValueError("Invalid time string")
            time = f"{{!field f=time op={operator}}}[{start} TO {end}]"
            search_dict["fq"] = time
        return search_dict

    @classmethod
    def get_metadata(
        cls, latest_version: bool = True, **search_dict: str
    ) -> SolrResponse:
        """Retrieve metadata from databrowser.

        Parameters
        ----------

        **search_dict: str
            Search query parameter

        Returns
        -------
        evaluation_system.model.solr.SolrResponse:
          NamedTuple of metadata on the search query results.
        """
        if latest_version:
            solrcore = cls(core="latest")
        else:
            solrcore = cls(core="files")
        return solrcore._retrieve_metadata(**search_dict)

    @staticmethod
    def search(latest_version=True, **partial_dict):
        """It mimics the same :class:`evaluation_system.model.file.DRSFile.search` behavior.
        The implementation contacts the required Solr cores instead of contacting the file system.

        :param latest_version: defines if looking for the latest version of a file only, or for any.
        :param partial_dict: the search dictionary for solr. It might also contain some special values as
         defined in :class:`SolrFindFiles._search`
        :returns: An iterator over the results."""
        # use defaults, if other required use _search in the SolrFindFiles instance
        if latest_version:
            s = SolrFindFiles(core="latest")
        else:
            s = SolrFindFiles(core="files")
        return s._search(**partial_dict)

    def _facets(self, latest_version=False, facets=None, **partial_dict):
        if facets and not isinstance(facets, list):
            if "," in facets:
                # we assume multiple values here
                facets = [f.strip() for f in facets.split(",")]
            else:
                facets = [facets]

        if "text" in partial_dict:
            partial_dict.update({"q": partial_dict.pop("text")})
        else:
            partial_dict.update({"q": "*:*"})

        query = self._to_solr_query(partial_dict)

        if facets is None:
            # get all minus what we don't want
            facets = set(self.solr.get_solr_fields()) - set(
                [
                    "",
                    "_version_",
                    "file_no_version",
                    "level",
                    "timestamp",
                    "time",
                    "creation_time",
                    "source",
                    "version",
                    "file",
                    "file_name",
                ]
            )

        if facets:
            query += (
                "&facet=true&facet.sort=index&facet.mincount=1&facet.field="
                + "&facet.field=".join(facets)
            )

        if latest_version:  # pragma: no cover (see above)
            query += "&group=true&group.field=file_no_version&group.facet=true"

        answer = self.solr.get_json("select?facet=true&rows=0&%s" % query)
        # TODO: why is there a language facit in the solr serach?
        answer = answer["facet_counts"]["facet_fields"]
        try:
            del answer["language"]
        except KeyError:
            pass
        return answer

    @staticmethod
    def facets(latest_version=True, facets=None, facet_limit=-1, **partial_dict):
        # use defaults, if other required use _search in the SolrFindFiles instance
        if latest_version:
            s = SolrFindFiles(core="latest")
        else:
            s = SolrFindFiles(core="files")
        return s._facets(facets=facets, latest_version=False, **partial_dict)
