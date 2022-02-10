#!/bin/env python
"""
This files encapsulates access to the esgf p2p system.
"""
import json
import urllib.request
import sys
import logging
import copy
from evaluation_system.misc.utils import Struct

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class P2P(object):
    """
    Handle the connection to a P2P over the Search API
    (check the `Search API documentation <http://esgf.org/wiki/ESGF_Search_API>`_.
    """

    TYPE = Struct.from_dict({"DATASET": "Dataset", "FILE": "File"})
    """Types of results that will be returned."""

    __MAX_RESULTS = 1000
    """Maximum number of items returned per call."""

    _time_out = 30
    """Specifies the time out (seconds) when trying to reach an index node."""

    def __init__(
        self,
        node="esgf-data.dkrz.de",
        api="esg-search/search",
        wget_api="esg-search/wget",
        defaults=None,
    ):
        """Creates a connection to the P2P search API.

        :param node: the p2p search node to connect to.
        :type node: str
        :param api: the url path of the service.
        :type api: str
        :param defaults: start the connection with the given defaults used for every search.
        :type defaults: dict
        """
        self.node = node
        self.api = api
        self.wget_api = wget_api
        self.defaults = defaults or {}

    def __str__(self):  # pragma: no cover
        return "P2P Search API connected to %s" % self.node

    def __repr__(self):  # pragma: no cover
        return "Search API: %s - defaults:%s" % (self.__get_url(), self.defaults)

    def set_defaults(self, defaults):
        """Set the defaults that will be used every time the node is contacted. For example::

            set_defaults(dict(project ='CMIP5'))

        :param defaults: defaults to use.
        :type defaults: dict"""
        self.defaults = defaults

    def get_defaults(self):
        """Return the defaults being currently used."""
        return copy.deepcopy(self.defaults)

    def reset_defaults(self):
        """Clear all defaults. It's the same as::

        set_defaults({})

        ."""
        self.defaults = {}

    def add_defaults(self, **defaults):
        """Adds values to the defaults for this connection.For example::

            add_defaults(project='CMIP5', product=['output1','output2'], institute_not_='MPI-M')

        This replaces but not removes existing keys."""
        self.defaults.update(defaults)

    def del_defaults(self, *def_keys):
        """Remove all the give defaults values if found. For example::

            del_defaults('institute','model')

        This would remove all values for both *institute* and *model* leaving everything else intact."""
        for k in def_keys:
            if k in self.defaults:
                del self.defaults[k]
            elif k + "_not_" in self.defaults:
                del self.defaults[k + "_not_"]

    def duplicate(self):
        """Create a duplicate of this p2p connection.

        :returns: A new instance of :class:`P2P` with the same configuration as this one."""
        return P2P(node=self.node, api=self.api, defaults=self.get_defaults())

    def __get_url(self):
        """Just return the url to this service from the values in this object"""
        return "http://%s/%s?format=application%%2Fsolr%%2Bjson" % (self.node, self.api)

    def __constraints_to_str(self, constraints, **defaults):
        """Transform the constraints passed into a url string. Apply defaults on top of it."""
        proc_const = []
        # work on a copy
        constraint_dict = self.defaults.copy()

        # apply the object wide defaults
        if constraints:
            constraint_dict.update(constraints)

        # if a method defines some defaults apply them on top
        # note this works with positive changes, you can't remove anything (yet)
        if defaults:
            constraint_dict.update(defaults)

        # encode constraints into query
        if constraint_dict:
            for key, value in constraint_dict.items():
                # negations might have been coded as <property>_not_ if not passed in a dictionary
                # just transform them to suffix '!'
                if key[-5:] == "_not_":
                    key = key[:-5] + "!"
                if isinstance(value, list):
                    value = ("&%s=" % key).join(map(str, value))
                proc_const.append("%s=%s" % (key, value))

        return "&".join(proc_const)

    def get_wget(self, **constraints):
        """:returns: (str) a string containing the wget script that can be used for downloading the selected files"""
        query = self.__constraints_to_str(constraints, type=P2P.TYPE.FILE)
        request = "http://%s/%s?%s" % (self.node, self.wget_api, query)
        return urllib.request.urlopen(request, None, self._time_out).read()

    def raw_search(self, query):
        """A raw search to the Solr index returning everything we get back.

        :returns: (dict) the raw result as returned from Solr using the search API."""
        request = "%s&%s" % (self.__get_url(), query)

        log.debug(request)
        response = json.load(urllib.request.urlopen(request, None, self._time_out))

        return response

    def search(self, type=TYPE.DATASET, **constraints):
        """Issue a query to the  P2P Search API from the constraint passed and return just the response
        (no headers).

        :param type: type of elements to return.
        :type type: :class:`P2P.TYPE`
        :param constraints: dictionary with any P2P Search API constraints.
        :returns: all documents returned from the P2P Search API."""
        query = self.__constraints_to_str(constraints, type=type)
        return self.raw_search(query)["response"]

    def get_datasets_names(self, batch_size=__MAX_RESULTS, **constraints):
        """:returns: a list of (datasets, version) tuples. (You can't define "fields" while calling this method)."""
        if "fields" in constraints:
            del constraints["fields"]
        datasets = set(
            [
                (d["master_id"], int(d["version"]))
                for d in self.datasets(
                    fields="master_id,version", batch_size=batch_size, **constraints
                )
            ]
        )
        return datasets

    def get_datasets(self, **constraints):
        """
        :returns: a list of dataset names. There's no limit imposed in the method itself, So it will
                  run out of memory if too many datasets are tried to be retrieved. Use the constraint limit=N to get
                  just the first "N" records.
        :param constraints: dictionary with any P2P Search API constraints."""

        return [d for d in self.datasets(**constraints)]

    def datasets(self, batch_size=__MAX_RESULTS, **constraints):
        """:returns: a generator iterating through the retrieve Solr docs.
        :param batch_size: defines the size of the retrieved batch. It means a query will
                           be sent to Solr every ``batch_size`` entries from the result set.
        :type batch_size: int
        :param constraints: dictionary with any P2P Search API constraints."""
        # if we have a limit use it also here.
        max_items = sys.maxsize
        try:
            max_items = int(constraints["limit"][0])
        except KeyError:
            # if not set the query limit to the batch size
            constraints["limit"] = batch_size
        try:
            sofar = int(constraints.pop("offset")[0])
        except KeyError:
            sofar = 0

        result = self.search(offset=sofar, **constraints)

        total = min(max_items, result["numFound"])
        retrieved = len(result["docs"])
        for d in result["docs"]:
            yield d

        while sofar + retrieved < total:
            result = self.search(offset=sofar + retrieved, **constraints)
            total = min(result["numFound"], max_items)
            for d in result["docs"]:
                yield d
            sofar += retrieved
            retrieved = len(result["docs"])

    def files(self, type=TYPE.FILE, **constraints):
        """the same as :class:`P2P.datasets`, but sets the type to 'File'. It's just a commodity function to
        improve readability.

        :param constraints: dictionary with any P2P Search API constraints."""
        return self.datasets(type=type, **constraints)

    def get_facets(self, *facets, **constraints):
        """
        :param facets: list of facets to query for.
        :param constraints: dictionary with any P2P Search API constraints.
        :returns: ([{facet:{facet_value:count}}]) the facets count from the server."""
        try:
            constraints = constraints.copy()
            del constraints["limit"]
        except KeyError:
            pass

        # facets encoded as a list
        if len(facets) == 1 and isinstance(facets[0], list):
            facets = facets[0]
        query = "%s&limit=0&facets=%s" % (
            self.__constraints_to_str(constraints),
            ",".join(facets),
        )

        response = self.raw_search(query)["facet_counts"]["facet_fields"]
        result = {}
        for facet in response:
            result[facet] = dict(zip(response[facet][0::2], response[facet][1::2]))
        return result

    @staticmethod
    def show(dictio, return_str=False):
        """Pretty print json (or any dict)"""
        json_str = json.dumps(dictio, sort_keys=True, indent=2)
        if return_str:
            return json_str
        print(json_str)

    @staticmethod
    def extract_catalog(dictio):
        """Extract the catalog from this json returned info. Only 1 catalog is expected."""
        if "url" in dictio:
            result = [
                e.split(".xml")[0] + ".xml"
                for e in dictio["url"]
                if e[-7:] == "Catalog"
            ]
            if result and len(result) == 1:
                return result[0]
            else:
                raise Exception("Can't find unique catalog")
