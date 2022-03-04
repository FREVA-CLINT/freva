"""
Created on 11.03.2013

@author: Sebastian Illing / estani

This package encapsulate access to a solr instance
"""

import urllib

from evaluation_system.model.solr_core import SolrCore


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

    def _to_solr_query(self, partial_dict):
        """Creates a Solr query assuming the default operator is "AND". See schema.xml for that."""
        params = []
        # these are special Solr keys that we might get and we assume are not meant for the search
        special_keys = "q fl fq facet.limit".split()

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
        return urllib.parse.urlencode(params)

    def _search(
        self,
        batch_size=10000,
        latest_version=False,
        _retrieve_metadata=False,
        **partial_dict,
    ):
        """This encapsulates the Solr call to get documents and returns an iterator providing the. The special
        parameter _retrieve_metadata will affect the first value returned by the iterator.

        :param batch_size: the amount of files to be buffered from Solr.
        :param latest_version: if the search should *try* to find the latest version from all contained here. Please note
         that we don't use this anymore. Instead we have 2 cores and this is defined directly in :class:`SolrFindFiles.search`.
         It was changed because it was slow and required too much memory.
        :param _retrieve_metadata: if set to true, the first item on the iterator is a metadata one. This is used so it can be
        known beforehand how many values are going to be returned, even before getting them all. To avoid this we might
        implement a result set object. But that would break the find_files compatibility."""
        offset = partial_dict.pop("start", 0)
        # value retrieved from sys.maxint and == 2**31-1
        max_rows = partial_dict.pop("rows", 2147483647)

        if "text" in partial_dict:
            partial_dict.update({"q": partial_dict.pop("text")})
        else:
            partial_dict.update({"q": "*:*"})

        if "fl" not in partial_dict:
            partial_dict.update({"fl": "file"})

        query = self._to_solr_query(partial_dict)
        # DEPRECATED:
        # This is not used anymore, because we have 2 different cores now
        if latest_version:  # pragma: no cover
            query += "&group=true&group.field=file_no_version&group.sort=version+desc&group.ngroups=true&group.format=simple"

        while True:
            if max_rows < batch_size:
                batch_size = max_rows
            answer = self.solr.get_json(
                "select?start=%s&rows=%s&%s" % (offset, batch_size, query)
            )
            if _retrieve_metadata:
                meta = answer["response"].copy()
                del meta["docs"]
                yield meta
                _retrieve_metadata = False
            # Not used anymore (see above)
            if latest_version:  # pragma: no cover
                offset = answer["grouped"]["file_no_version"]["doclist"]["start"]
                total = answer["grouped"]["file_no_version"]["ngroups"]
                iter_answer = answer["grouped"]["file_no_version"]["doclist"]["docs"]
            else:
                offset = answer["response"]["start"]
                total = answer["response"]["numFound"]
                iter_answer = answer["response"]["docs"]

            for item in iter_answer:
                yield item["file"]

            max_rows -= total
            if total - offset <= batch_size or max_rows <= 0:
                break  # we are done
            else:
                offset += batch_size

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
        return s._search(latest_version=False, **partial_dict)

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
