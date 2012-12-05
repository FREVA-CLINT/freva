#!/bin/env python
"""
CREATES A REQUEST TO P2P SEARCH API BASED ON CONSTRAINTS GIVEN AS INPUT PARAMETERS

"""
import json
import re
import urllib2
import sys
import logging
import copy
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class Utils(object):
    class Struct(object):
        """This class is used for converting dictionaries into classes."""

        def __init__(self, **entries):
            self.__dict__.update(entries)

        def __getattr__(self, name):
            return None

        def toDict(self):
            """Transfrom this struct to a dictionary."""
            result = {}
            for i in self.__dict__:
                if isinstance(self.__dict__[i], Struct): result[i] = self.__dict__[i].toDict()
                else: result[i] = self.__dict__[i]
            return result

        def __repr__(self):
            def to_str(val):
                if isinstance(val, basestring): return "'" + val + "'"
                return val

            return "<%s>" % ",".join([ "%s:%s" % (att, to_str(self.__dict__[att]))
                                        for att in self.__dict__ if not att.startswith('_')])

    @staticmethod
    def to_obj(dictionary, recurse=False):
        dictionary = copy.deepcopy(dictionary)

        #we don't need to recurse if this is not a non-empty iterable sequence
        if not dictionary: return dictionary

        #If a list, apply to elements within
        if type(dictionary) == list: return map(lambda d: to_obj(d, recurse) ,dictionary)
        #not a dictionary, return unchanged
        if type(dictionary) != dict: return dictionary
        if recurse:
            for key in dictionary: dictionary[key] = to_obj(dictionary[key], recurse)

        return Utils.Struct(**dictionary)



class P2P(object):
    """Handle the connection to a p2p Index node"""

    TYPE = Utils.to_obj({'DATASET':'Dataset','FILE':'File'})

    __MAX_RESULTS = 1000
    """Maximum number of items returned per call"""

    _time_out = 30
    """Specifies the time out (seconds) when trying to reach an index node"""


    def __init__(self, node='esgf-data.dkrz.de', api='esg-search/search', wget_api='esg-search/wget', defaults=None):
        """
	    Generates a p2p connection.
	    node := the p2p search node to connect to.
	    api := the url path of the service
	    defaults := start the connection with the given defaults
	"""
        self.node = node
        self.api = api
        self.wget_api = wget_api
        self.defaults = (defaults or {})
        
    def __str__(self): return 'P2P Search API connected to %s' % self.node
    def __repr__(self): return 'Search API: %s - defaults:%s' % (self.__get_url(), self.defaults)
    

    def set_defaults(self, defaults):
        """Set the defaults (dict) that will be used everytime the node is contacted 
e.g. {'project':'CMIP5'}"""
        self.defaults = defaults

    def get_defaults(self): 
        """Return the defaults set"""
        return copy.deepcopy(self.defaults)

    def reset_defaults(self): 
        """Clear all defaults (same as set_defaults({})"""
        self.defaults = {}

    def add_defaults(self, **defaults): 
        """Adds values to the defaults of this p2p connection
E.g. add_defaults(project='CMIP5', product=['output1','output2'], institute_not_='MPI-M')"""
        self.defaults.update(defaults)

    def del_defaults(self, *def_keys):
        """Remove all the give defaults values if found
E.g. del_defaults('institute','model')""" 
        for k in def_keys: 
            if k in self.defaults: del self.defaults[k]
            elif k + '_not_' in self.defaults: del self.defaults[k + '_not_']


    def duplicate(self):
        """Create a duplicate of this p2p connection."""
        return P2P(node=self.node, api=self.api, defaults=self.get_defaults())


    def __get_url(self):
        """Just return the url to this service from the values in this object"""
        return 'http://%s/%s?format=application%%2Fsolr%%2Bjson' % (self.node, self.api)

    def __constraints_to_str(self, constraints, **defaults):
        """Transform the constraints passed into a url string. Apply defaults on top of it."""
        proc_const = []
        #work on a copy
        constraint_dict = self.defaults.copy()

        #apply the object wide defaults
        if constraints: constraint_dict.update(constraints)

        #if a method defines some defaults apply them on top
        #note this works with positive changes, you can't remove anything (yet)
        if defaults: constraint_dict.update(defaults)
        
        #encode constraints into query
        if constraint_dict:
            for key, value in constraint_dict.items():
                #negations might have been coded as <property>_not_ if not passed in a dictionary
                #just transform them to suffix '!'
                if key[-5:] == '_not_': key = key[:-5] + '!'
                if isinstance(value, list): value = ('&%s=' % key).join(map(str, value))
                proc_const.append('%s=%s' % (key, value))

        return '&'.join(proc_const)
    
    def get_wget(self, **constraints):
        """Returns a string containing the wget script used for downloading the selected files""" 
        query = self.__constraints_to_str(constraints, type=P2P.TYPE.FILE)
        request = 'http://%s/%s?%s' % (self.node, self.wget_api, query)
        return urllib2.urlopen(request, None,  self._time_out).read()
        
    def raw_search(self, query):
        """A raw search to the Solr index returning everything we get back."""
        request = '%s&%s' % (self.__get_url(), query)

        log.debug(request)
        print request
        response = json.load(urllib2.urlopen(request, None,  self._time_out))

        return response

    def search(self, type=TYPE.DATASET, **constraints):
        """Constructs a P2P Search API from the constraint passed and return just the response
(no headers). Default type=Dataset."""
        query = self.__constraints_to_str(constraints, type=type)
        return self.raw_search(query)['response']

    def get_datasets_names(self, batch_size=__MAX_RESULTS, **constraints):
        """returns a list of (datasets, version) tuppels. You can't define "fields"
while calling this method"""
        if 'fields' in constraints: 
            del constraints['fields']
        datasets = set([(d['master_id'], int(d['version'])) for d in self.datasets(
                        fields='master_id,version',batch_size=batch_size,**constraints)])
        return datasets

    def get_datasets(self, **constraints):
        """returns a list of dataset. There's no limit imposed in the method itself, So it will
run out of memory if too many dataset are tried to be retireved. use limit=N to get
just the first "N" records."""

        return [d for d in self.datasets(**constraints)]

    def datasets(self, batch_size=__MAX_RESULTS, **constraints):
        """returns a generator iterating thorugh the complete resulting docs.
batch_size := defines the size of the retrieved batch
limit := limits the total number of returned docs

all other solar constraints apply"""
        #if we have a limit use it also here.
        max_items = sys.maxint
        if 'limit' in constraints:
            max_items = int(constraints['limit'])
        else:
            #if not set the query limit to the batch size
            constraints['limit'] = batch_size
        if 'offset' in constraints:
            sofar = int(constraints['offset'])
            del constraints['offset']
        else:
            sofar = 0

        result = self.search(offset=sofar, **constraints)


        total = min(max_items, result['numFound'])
        retrieved = len(result['docs'])
        datasets = {}
        for d in result['docs']:
            yield d
        
        while sofar + retrieved < total:
            result = self.search(offset=sofar+retrieved,**constraints)
            total = min(result['numFound'], max_items)
            for d in result['docs']:
                yield d
            sofar += retrieved
            retrieved = len(result['docs'])

    def files(self, type=TYPE.FILE, **constraints):
        """the same as datasets, but sets the type to 'File'. It's just a commodity function to
improve readability"""
        return self.datasets(type=type, **constraints)

    def get_facets(self, *facets, **constraints):
        """Return the facet count from the server or the given facets (as parameters or list)
return {facet:{facet_value:count}}"""
        if 'limit' in constraints:
            constraints = constraints.copy()
            del constraints['limit']

        #facets encoded as a list
        if len(facets)==1 and isinstance(facets[0], list): facets=facets[0]
        query= '%s&limit=0&facets=%s' % (self.__constraints_to_str(constraints), ','.join(facets))

        response = self.raw_search(query)['facet_counts']['facet_fields']
        result = {}
        for facet in response:
            result[facet] = dict(zip(response[facet][0::2], response[facet][1::2]))
        return result



    @staticmethod
    def show(dictio, return_str=False):
        """Pretty print json (or any dict)"""
        str = json.dumps(dictio, sort_keys=True, indent=2)
        if return_str: return str
        print str

    @staticmethod
    def extract_catalog(dictio):
        """Extract the catalog from this json returned info. Only 1 cataog is expected"""
        if 'url' in dictio:
            result = [ e.split('.xml')[0]+'.xml' for e in dictio['url'] if e[-7:] == 'Catalog']
            if result and len(result) == 1:
                return result[0]
            else:
                raise Exception("Can't find unique catalog")


#**** COMMAND LINE ****
def auto_doc(message=''):
    import re, sys, os
    file = sys.argv[0]

    re_start = re.compile('.*\*!!!\*$')
    re_end = re.compile('^[ \t]*$')
    re_entries= re.compile("^[^']*'([^']*)'[^']*(?:'([^']*)')?[^#]*#(.*)$")
    parsing=False
    results = []
    for line in open(file, 'r'):
        if parsing:
            items = re_entries.match(line)
            if items:
                flag, flag_opt, mesg = items.groups()
                if flag_opt: flag = '%s, %s' % (flag, flag_opt)
                results.append('  %-20s : %s' % (flag, mesg))
            if re_end.match(line): break
        elif re_start.match(line): parsing = True

    if results: print '%s%s [opt]\nopt:\n%s' % (message, os.path.basename(file), '\n'.join(results))
    else: print '%s %s' % (os.path.basename(file), message)

def usage(message=None):
    if message: auto_doc(message)
    else: auto_doc()


def main(argv=None):
    import getopt
    import re
    facet_pat = re.compile(r'(.*[^\\])=(.*)')

    if argv is None: argv = sys.argv[1:]
    try:
        args, lastargs = getopt.getopt(argv, "f:hd", ['help', 'debug', 'facet=','query=', 'list-datasets', 'show-facet='])
    except getopt.error:
        print sys.exc_info()[:3]
        return 1

    DEBUG = False
    datasets = False
    facets = {}
    query=None
    show_facets = []
    #parse arguments *!!!*
    for flag, arg in args:
        if flag=='-f' or flag=='--facet':   #       Set facet for search (e.g. institute=MPI) can be used multiple times.
            facet, value = facet_pat.match(arg).groups()
            if facet in facets:
                #accept same value multiple times!
                if not isinstance(facets[facet], list): facets[facet] = [facets[facet]]
                facets[facet].append(value)
            else: 
                facets[facet] = value
        elif flag=='--show-facet':         #<list> :List all values for the given facet (might be defined multiple times)
             show_facets.append(arg)
        elif flag=='--list-datasets':       #       List datasets found using the p2p interface
            datasets = True
        elif flag=='--query':               #<list> :Display results from <list> queried fields
            query=arg
        elif flag == '-d' or flag == '--debug': #turn on debuging info
            DEBUG = True
        elif flag=='-h' or flag=='--help':        #This help
            usage('Interact with p2p index nodes via the search API\n')
            return 0


    #if empty leave it alone    
    #handle constraints as the last items in the argument list
    for arg in lastargs:
        if '=' not in arg:
            raise CommandError("Invalid format for query: %s" % arg)
        
        items = arg.split('=')
        if len(items==1):
            facets[items[0]] = True
        else:
            facets[items[0]] = '='.join(items[1:])
        
    if DEBUG:
        sys.stderr.write("Searching string: %s\n" % search_dict)

    p2p = P2P()

    if datasets: print '\n'.join(['%s#%s' % d for d in sorted(p2p.get_datasets_names(**facets))])
    if query: 
        if len(query.split(',')) > 1:
            #we get multiple fields queried, return in a tructured fashion
            p2p.show(p2p.get_datasets(fields=query,**facets))
        else:
            #if only one then return directly
            print '\n'.join([str(d[query]) for d in p2p.get_datasets(fields=query,**facets)])
        
    if show_facets:
        results = p2p.get_facets(show_facets, **facets)
        #render them
        for facet_key in sorted(results):
            print '[%s]\n\t%s' % (facet_key, '\n\t'.join([ '%s: %s' % (k,results[facet_key][k])  for k in sorted(results[facet_key])]))
    return 0
            


if __name__ == '__main__':
    import sys
    result=main(None)
    if isinstance(result, int):
        if result != 0: usage()
        sys.exit(result)


