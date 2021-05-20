"""
Created on 11.03.2013

@author: Sebastian Illing / estani

This package encapsulate access to a solr instance (not for search but for administration)
We define two cores::

* files: all files  - id is file (full file path)
* latest: only those files from the latest dataset version - id is file_no_version (full file path *wothout* version information)

"""

import os
import shutil
import urllib
import urllib.request
import json
from datetime import datetime
import logging
log = logging.getLogger(__name__)

from evaluation_system.model.file import DRSFile
from evaluation_system.misc import config


class META_DATA(object):
    """This class just holds some values for the dump file parsing/writing. Here a small example::

  crawl_dir /some/dir
  
  data
  /some/dir/some/other/subdir/file1.nc,123123.0
  /some/dir/some/other/subdir/file2.nc,123123.230
  /some/dir/yet/another/subdir/file.nc,123123.230
  ...

See more info on :class:`SolrCore.dump_fs_to_file` and :class:`SolrCore.load_fs_from_file`"""

    CRAWL_DIR = 'crawl_dir'
    "The path to the directory that was crawled and from which the following list of files comes."
    
    DATA = 'data'
    "Marks the end of the metadata area. What follows is a list of filepaths and timestamps separated by a line break."


class SolrCore(object):
    """Encapsulate access to a Solr instance"""
    
    def __init__(self, core=None, host=None, port=None, echo=False, instance_dir=None, data_dir=None, get_status=True):
        """Create the connection pointing to the proper solr url and core.

:param core: The name of the core referred (default: loaded from config file)
:param host: the hostname of the Solr server (default: loaded from config file)
:param port: The port number of the Solr Server (default: loaded from config file)
:param echo: If True, show all urls before issuing them.
:param instance_dir: the core instance directory (if empty but the core exists it will get downloaded from Solr)
:param data_dir: the directory where the data is being kept (if empty but the core exists it will
get downloaded from Solr)"""

        if host is None:
            host = config.get(config.SOLR_HOST)
        if port is None:
            port = config.get(config.SOLR_PORT)
        if core is None:
            core = config.get(config.SOLR_CORE)
            
        self.solr_url = 'http://%s:%s/solr/' % (host, port)
        self.core = core
        self.core_url = self.solr_url + core + '/'
        self.echo = echo
        self.instance_dir = instance_dir
        self.data_dir = data_dir
    
        if get_status:
            st = self.status()
        else:
            st = {}
        if self.instance_dir is None and 'instanceDir' in st:
            self.instance_dir = st['instanceDir']
        if self.data_dir is None and 'dataDir' in st:
            self.data_dir = st['dataDir']
        else:
            self.data_dir = 'data'
        
        # Other Defaults
        import socket
        socket.setdefaulttimeout(20)
            
    def __str__(self):
        return '<SolrCore %s>' % self.core_url
        
    def post(self, list_of_dicts, auto_list=True, commit=True):
        """Sends some json to Solr for ingestion.

:param list_of_dicts: either a json or more normally a list of json instances that will be sent to Solr for ingestion
:param auto_list: avoid packing list_of dicts in a directory if it's not one
:param commit: send also a Solr commit so that changes can be seen immediately."""
        if auto_list and not isinstance(list_of_dicts, list):
            list_of_dicts = [list_of_dicts]
        endpoint = 'update/json?'
        if commit:
            endpoint += 'commit=true'

        query = self.core_url + endpoint
        if self.echo:
            log.debug(query)
        post_data = json.dumps(list_of_dicts).encode('ascii')
        req = urllib.request.Request(query, post_data)
        req.add_header("Content-type", "application/json")

        return urllib.request.urlopen(req).read()

    def get_json(self, endpoint, use_core=True, check_response=True):
        """Return some json from server. Is the raw access to Solr.
        
:param endpoint: The endpoint, path missing after the core url and all parameters encoded in it (e.g. 'select?q=*')
:param use_core: if the core info is used for generating the endpoint. (if False, then == self.core + '/' + endpoint)
:param check_response: If the response should be checked for errors. If True, raise an exception if something is
 wrong (default: True)"""
        if '?' in endpoint:
            endpoint += '&wt=json'
        else:
            endpoint += '?wt=json'
        
        if use_core:
            query = self.core_url + endpoint
        else:
            query = self.solr_url + endpoint
        if self.echo:
            log.debug(query)
        
        req = urllib.request.Request(query)
        response = json.loads(urllib.request.urlopen(req).read())
        if response['responseHeader']['status'] != 0:
            raise Exception("Error while accessing Core %s. Response: %s" % (self.core, response))
        
        return response
    
    def get_solr_fields(self):
        """Return information about the Solr fields. This is dynamically generated and because of
dynamicFiled entries in the Schema, this information cannot be inferred from anywhere else."""
        answer = self.get_json('admin/luke')['fields']
        #TODO: Solr has a language facet. Until we know why, delete it
        if isinstance(answer, dict):
            try:
                del answer['language']
            except KeyError:
                pass
        else:
            try:
                answer.remove('language')
            except ValueError:
                pass
        return answer
    
    def create(self, instance_dir=None, data_dir=None, config='solrconfig.xml', schema='schema.xml', check_if_exist=True):
        """Creates (actually "register") this core. The Core configuration and directories must
be generated beforehand (not the data one). You may clone an existing one or start from scratch.

:param instance_dir: main directory for this core
:param data_dir: Data directory for this core (if left unset, a local "data" directory in instance_dir will be used)
:param config: The configuration file (expected in instance_dir/conf)
:param schema: The schema file (expected in instance_dir/conf)
:param check_if_exist: check for the existence of the instance directorie"""
        # check basic configuration (it must exists!)
        if instance_dir is None and self.instance_dir is None:
            raise ValueError("No Instance directory defined!")
        elif instance_dir is not None:
            self.instance_dir = instance_dir
        if not os.path.isdir(self.instance_dir) and check_if_exist:
            raise FileNotFoundError("Expected Solr Core configuration not found in %s" % self.instance_dir)
        
        if data_dir is not None:
            self.data_dir = data_dir
        
        return self.get_json('admin/cores?action=CREATE&name=%s' % self.core
                                + '&instanceDir=%s' % self.instance_dir
                                + '&config=%s' % config
                                + '&schema=%s' % schema
                                + '&dataDir=%s' % self.data_dir, use_core=False
                             )
    
    def reload(self):
        """Reload the core. Useful after schema changes.
Be aware that you might need to re-ingest everything if there were changes to the indexing part of the schema."""
        return self.get_json('admin/cores?action=RELOAD&core=' + self.core, use_core=False)
    
    def unload(self):
        """Unload the core."""
        return self.get_json('admin/cores?action=UNLOAD&core=' + self.core, use_core=False)
    
    def swap(self, other_core):
        """Will swap this core with the given one (that means rename their references)
        
:param other_core: the name of the other core that this will be swapped with."""
        return self.get_json('admin/cores?action=SWAP&core=%s&other=%s' % (self.core, other_core), use_core=False)
    
    def status(self, general=False):
        """Return status information about this core or the whole Solr server.

:param general: If True return all information as provided by the server, otherwise just the status info
from this core."""
        url_str = 'admin/cores?action=STATUS'
        if not general:
            url_str += '&core=' + self.core
        response = self.get_json(url_str, use_core=False)
        if general:
            return response
        else:
            print(response['status'][self.core])
            return response['status'][self.core]
    
    def clone(self, new_instance_dir, data_dir='data', copy_data=False):
        """Copies a core somewhere else.
:param new_instance_dir: the new location for the clone.
:param data_dir: the location of the data directory for this new clone.
:param copy_data: If the data should also be copied (Warning, this is done on the-fly so be sure to unload the core
first) or assure otherwise there's no chance of getting corrupted data (I don't know any other way besides
unloading the original code))"""
        try:
            os.makedirs(new_instance_dir)
        except:
            pass
        shutil.copytree(os.path.join(self.instance_dir, 'conf'), os.path.join(new_instance_dir, 'conf'))
        if copy_data:
            shutil.copytree(os.path.join(self.instance_dir, self.data_dir), os.path.join(new_instance_dir, data_dir))
    
    def delete(self, query):
        """Issue a delete command, there's no default query for this to avoid unintentional deletion."""
        self.post(dict(delete=dict(query=query)), auto_list=False)

    @staticmethod
    def dump_fs_to_file(start_dir, dump_file,  batch_size=1000, check=False, abort_on_errors=False):
        """This is the currently used method for ingestion. This method generates a file with
a listing of paths and timestamps from the file system. The syntax of the file looks like this::

  crawl_dir    /path/to/some/directory
  
  data
  /path/to/a/file,1239879.0
  /path/to/another/file,1239879.0
  ...

The crawl_dir indicates the directory being crawled and results in the deletion of all files whose path starts with
that one (i.e. everything under that path will be *replaced*).

Generating this file takes at least 8 hours for the whole /miklip/integration/data4miklip directory. It would be
nice to generate it in a different manner (e.g. using the gpfs policy API).

:param start_dir: The directory from which the file system will be crawled
:param dump_file: the path to the file that will contain the dump. if the file ends with '.gz' the resulting file
will be gziped (preferred)
:param batch_size: number of entries that will be written to disk at once. This might help pin-pointing crashes.
:param check: if the paths should be checked. While checking path the resulting paths are guaranteed to be accepted
later on normally this is too slow for this phase, so the default is False.
:param abort_on_errors: If dumping should get aborted as soon as an error is found, i.e. a file that can't be ingested.
 Most of the times there are many files being found that are no data at all."""

        log.debug('starting sequential ingest')
        open_method, mode = open, 'w'
        if dump_file.endswith('.gz'):
            # print "Using gzip"
            import gzip
            open_method, mode = gzip.open, 'wt'
        with open_method(dump_file, mode) as f:
            batch_count = 0
            
            # store metadata
            f.write('%s\t%s\n' % (META_DATA.CRAWL_DIR, start_dir))
            
            # store data
            f.write('\n%s\n' % META_DATA.DATA)
            for path in dir_iter(start_dir):
                if check:
                    try:
                        DRSFile.from_path(path)
                    except:
                        if abort_on_errors:
                            raise
                        else:
                            print(f"Error ingesting {path}")
                            continue
                ts = os.path.getmtime(path)
                f.write('%s,%s\n' % (path, ts))
                batch_count += 1
                if batch_count >= batch_size:
                    f.flush()

    @staticmethod
    def load_fs_from_file(dump_file, batch_size=10000, abort_on_errors=False, core_all_files=None, core_latest=None):
        """This is the opposite method of :class:`SolrCore.dump_fs_to_file`. It loads the files system information to Solr
from the given file. The syntax is defined already in the mentioned dump method.
Contrary to what was previously done, this method loads the information from a file and decides if it should be added
to just the common file core, holding the index of all files, or also to the *latest* core, holding information
about the latest version of all files (remember that in CMIP5 not all files are version, just the datasets).

:param dump_file: the path to the file that contains the dump. if the file ends with '.gz' the file is assumed to
be gziped.
:param batch_size: number of entries that will be written to the Solr main core (the latest core will be flushed at
the same time and is guaranteed to have at most as many as the other.
:param abort_on_errors: If dumping should get aborted as soon as an error is found, i.e. a file that can't be ingested.
 Most of the times there are many files being found in the dump file that are no data at all
:param core_all_files: if desired you can pass the SolrCore managing all the files (if not the one named 'files'will
be used, using the configuration from the config file).
:param core_latest: if desired you can pass the SolrCore managing the latest file versions (if not the one named
'latest' will be used, using the configuration from the config file).
"""
        open_method, mode = open, 'r'
        if dump_file.endswith('.gz'):
            # print "Using gzip"
            import gzip
            open_method, mode = gzip.open, 'rt'
        if core_latest is None:
            core_latest = SolrCore(core='latest')
        if core_all_files is None:
            core_all_files = SolrCore(core='files')
        with open_method(dump_file, mode) as f:
            batch_count = 0
            batch = []
            batch_latest = []
            batch_latest_new = {}

            latest_versions = {}
            
            header = True
            
            import re
            meta = re.compile('[^ \t]{1,}[ \t]{1,}(.*)$')
            
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if header:
                    if line.startswith(META_DATA.CRAWL_DIR):
                        crawl_dir = meta.match(line).group(1).strip()
                        # we should delete these. We need to scape the first slash since Solr
                        # will expect a regexp if not (new to Solr 4.0)
                        core_all_files.delete('file:\\%s*' % crawl_dir)
                        core_latest.delete('file:\\%s*' % crawl_dir)
                    elif line.startswith(META_DATA.DATA):
                        header = False
                    continue
                else:
                    file_path, timestamp = line.split(',')
                    try:
                        drs_file = DRSFile.from_path(file_path)
                        
                        metadata = SolrCore.to_solr_dict(drs_file)
                        ts = float(timestamp)
                        metadata['timestamp'] = ts
                        metadata['creation_time'] = timestamp_to_solr_date(ts)
    
                        batch.append(metadata)
                        
                        if drs_file.is_versioned():
                            version = latest_versions.get(drs_file.to_dataset(versioned=False), None)
                            if version is None or drs_file.get_version() > version:
                                # unknown or new version, update
                                version = drs_file.get_version()
                                latest_versions[drs_file.to_dataset(versioned=False)] = version
                                batch_latest_new[drs_file.to_dataset(versioned=False)] = metadata
                                #batch_latest = batch_latest_new.values()
                
                            if not drs_file.get_version() < version:
                                # print latest_versions
                                #print drs_file.get_version(), version, metadata
                                batch_latest.append(metadata)
                        else:
                            # if not version always add to latest
                            batch_latest_new[drs_file.to_dataset(versioned=False)] = metadata
                            batch_latest.append(metadata)

                        if len(batch) >= batch_size:
                            print("Sending entries %s-%s" % (batch_count * batch_size, (batch_count+1) * batch_size))
                            core_all_files.post(batch)
                            batch = []
                            batch_count += 1
                            if batch_latest:
                                core_latest.post(batch_latest)
                                batch_latest = []
                                batch_latest_new = {}
                    except:
                        print(f"Can't ingest file {file_path}")
                        if abort_on_errors:
                            raise

            # flush
            if len(batch) > 0:
                print("Sending last %s entries and %s entries to latest core" % (len(batch), len(batch_latest)))
		#print len(batch_latest)
                core_all_files.post(batch)
                batch = []
                batch_count += 1
                if batch_latest:
                    core_latest.post(batch_latest)
                    batch_latest = []
                
    
    @staticmethod
    def to_solr_dict(drs_file):
        """Extracts from a DRSFile the information that will be stored in Solr"""
        metadata = drs_file.dict['parts'].copy()
        metadata['file'] = drs_file.to_path()
        if 'version' in metadata:
            metadata['file_no_version'] = metadata['file'].replace('/%s/' % metadata['version'], '/')
        else:
            metadata['file_no_version'] = metadata['file']
        metadata['data_type'] = drs_file.drs_structure
        # metadata['timestamp'] = float(timestamp)
        # metadata['dataset'] = drs_file.to_dataset()
        
        return metadata
    
    # def dump(self, dump_file=None, batch_size=10000, sort_results=False):
    #     """Dump a list of files and their timestamps that can be ingested afterwards"""
    #     if dump_file is None:
    #         # just to store where and how we are storing this
    #         dump_file = datetime.now().strftime('/miklip/integration/infrastructure/solr/backup_data/%Y%m%d.csv.gz')
    #
    #     def cache(batch_size):
    #         offset = 0
    #         while True:
    #             url_query = 'select?fl=file,timestamp&start=%s&rows=%s&q=*' % (offset, batch_size)
    #             if sort_results:
    #                 url_query += '&sort=file+desc'
    #             print "Calling %s" % url_query
    #             answer = self.get_json(url_query)
    #             offset = answer['response']['start']
    #             total = answer['response']['numFound']
    #             for item in answer['response']['docs']:
    #                 yield (item['file'], item['timestamp'],)
    #             if total - offset <= batch_size:
    #                 break   # we are done
    #             else:
    #                 offset += batch_size
    #
    #     if dump_file.endswith('.gz'):
    #         import gzip
    #         # the with statement support started with python 2.7 (http://docs.python.org/2/library/gzip.html)
    #         # Let's leave this python 2.6 compatible...
    #         f = gzip.open(dump_file, 'wb')
    #     else:
    #         f = open(dump_file, 'w')
    #
    #     try:
    #         # store metadata
    #         f.write('%s\t%s\n' % (META_DATA.CRAWL_DIR, '/'))
    #
    #         # store data
    #         f.write('\n%s\n' % META_DATA.DATA)
    #         for file_path, timestamp in cache(batch_size):
    #             f.write('%s,%s\n' % (file_path, timestamp))
    #     finally:
    #         f.close()

    
def timestamp_to_solr_date(timestamp):
    """Transform a timestamp (float) into a string parsable by Solr"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')

# -- These are for multiple processes...
# but There's no benefit for having multiple threads at this time
# on the contrary, it's worse :-/
# There's no improvement for not having this construct either, so I'm leaving it
# here. It might help in the future...
# def search_iter(data_types, search_dict):
#     if not isinstance(data_types, list):
#         data_types = [data_types]
#     for data_type in data_types:
#         for file_path in DRSFile.search(data_type, latest_version=False, path_only=True, **search_dict):
#             yield file_path
#     # yield SolrCore.to_solr_dict(drs_file)
#
#
def dir_iter(start_dir, abort_on_error=True, followlinks=True):
    for base_dir, dirs, files in os.walk(start_dir, followlinks=followlinks):
        # make sure we walk them in the proper order (latest version first)
        dirs.sort(reverse=True)
        files.sort(reverse=True)    # just for consistency

        for f in files:
            yield os.path.join(base_dir, f)
#
#
# def enqueue_from_search(q, data_types, search_dir):
#     for metadata in search_iter(data_types, search_dir):
#         q.put(metadata)
#
#
# def enqueue_from_dir(q, start_dir, abort_on_error=True):
#     for metadata in dir_iter(start_dir, abort_on_error=abort_on_error):
#         q.put(metadata)
#
#
# def handle_file_init(q, core, batch_size=10000):
#     handle_file.batch_size = batch_size
#     handle_file.running = True
#     handle_file.q = q
#     handle_file.core = core
#
#
# def handle_file(number, end_token):
#     print "starting proc %s" % number
#     batch_count = 0
#     batch = []
#     solr = SolrCore(core=handle_file.core)
#     while handle_file.running:
#         path = handle_file.q.get()
#         if path == end_token:
#             handle_file.q.put(end_token)
#             break
#         value = SolrCore.to_solr_dict(DRSFile.from_path(path))
#         # import scipy.io.netcdf
#         # with scipy.io.netcdf.netcdf_file(value['file'], 'r') as f:
#         #    value.update(f._attributes)
#         ts = os.path.getmtime(value['file'])
#         value['timestamp'] = ts
#         value['creation_time'] = timestamp_to_solr_date(ts)
#         batch.append(value)
#         if len(batch) >= handle_file.batch_size:
#             print "Sending entries %s-%s from %s" % (batch_count * handle_file.batch_size,
#                                                      (batch_count+1) * handle_file.batch_size, number)
#             solr.post(batch)
#             batch = []
#             batch_count += 1
#
#     if batch:
#         print "Sending last %s entries from %s." % (len(batch), number)
#         solr.post(batch)
#     print "proc %s done!" % number
