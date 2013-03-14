'''
Created on 13.03.2013

@author: estani
'''
'''
Created on 11.03.2013

@author: estani

This package encapsulate access to a solr instance (not for search but for administration)
'''

import os
import shutil
import urllib2
import json
from datetime import datetime

from evaluation_system.model.file import DRSFile, BASELINE0, BASELINE1, CMIP5, OBSERVATIONS, REANALYSIS


class SolrCore(object):
    """Encapsulate access to a Solr instance"""
    
    def __init__(self, core, host='localhost', port=8983, echo=False, instance_dir=None, data_dir=None):
        """Create the connection pointing to the proper solr url and core"""
        self.solr_url = 'http://%s:%s/solr/' % (host, port)
        self.core = core
        self.core_url = self.solr_url + core + '/'
        self.echo = echo
        self.instance_dir = instance_dir
        self.data_dir = data_dir
    
        st = self.status()
        if self.instance_dir is None and 'instanceDir' in st:
            self.instance_dir = st['instanceDir']
        if self.data_dir is None and 'dataDir' in st:
            self.data_dir = st['dataDir']
        else:
            self.data_dir = 'data'
        
    def post(self, list_of_dicts, auto_list=True):
        """Sends some json to Solr"""
        if auto_list and not isinstance(list_of_dicts, list): list_of_dicts=[list_of_dicts]
        
        req=urllib2.Request(self.core_url + 'update/json?commit=true', json.dumps(list_of_dicts))
        req.add_header("Content-type", "application/json")
        
        if self.echo:
            print req.get_full_url()
        
        return urllib2.urlopen(req).read()
    
    def get_json(self, endpoint, use_core=True, check_response=True):
        """Return some json from server"""
        if '?' in endpoint:
            endpoint += '&wt=json'
        else:
            endpoint += '?wt=json'
        
        if use_core:
            req=urllib2.Request(self.core_url + endpoint)    
        else:
            req=urllib2.Request(self.solr_url + endpoint)    
        
        if self.echo:
            print req.get_full_url()
        
        response = json.loads(urllib2.urlopen(req).read())
        if response['responseHeader']['status'] != 0:
            raise "Can't reload core %s! Response: %s" % (self.core, response)
        
        return response
    
    def get_solr_fields(self):
        """Return information about the Solr fields"""
        return self.get_json('admin/luke')['fields']
    
    def create(self, instance_dir=None, data_dir=None, config='solrconfig.xml', schema='schema.xml'):
        """Creates (actually "register") this core. The Core configuration and directories must
be generated beforehand (not the data one). You may clone an existing one or start from scratch.

:param instance_dir: main directory for this core
:param data_dir: Data directory for this core (if left unset, a local "data" directory in instance_dir will be used)
:param config: The configuration file (expected in instance_dir/conf)
:param schema: The schema file (expected in instance_dir/conf)"""
        #check basic configuration (it must exists!)
        if instance_dir is None and self.instance_dir is None:
            raise Exception("No Instance directory defined!")
        elif instance_dir is not None:
            self.instance_dir = instance_dir
        if not os.path.isdir(self.instance_dir):
            raise Exception("Expected Solr Core configuration not found in %s" % self.instance_dir)
        
        if data_dir is not None:
            self.data_dir = data_dir
        
        return self.get_json('admin/cores?action=CREATE&name=%s' % self.core
                    + '&instanceDir=%s' % self.instance_dir
                    + '&config=%s' % config
                    + '&schema=%s' % schema
                    + '&dataDir=%s' % self.data_dir, use_core=False)
    
    def reload(self):
        """Reload the core. Usefull after schema changes.
Be aware that you might need to reingest everything if there were changes to the indexing part of the schema."""
        return self.get_json('admin/cores?action=RELOAD&core=' + self.core, use_core=False)
    
    def unload(self):
        """Unload the core."""
        return self.get_json('admin/cores?action=UNLOAD&core=' + self.core, use_core=False)
    
    def swap(self, other_core):
        """Will swap this core with the given one (that means rename their references)"""
        return self.get_json('admin/cores?action=SWAP&core=%s&other=%s' % (self.core, other_core), use_core=False)
    
    def status(self, general=False):
        """Return status information about this core or the whole Solr server.

:param general: If True return all information as provided by the server, otherwise just the status info from this core."""
        url_str = 'admin/cores?action=STATUS'
        if not general:
            url_str += '&core=' + self.core
        response = self.get_json(url_str, use_core=False)
        if general:
            return response
        else:
            return response['status'][self.core]
    
    def clone(self, new_instance_dir, data_dir='data', copy_data=False):
        """Copies a core somewhere else.
:param new_instance_dir: the new location for the clone.
:param data_dir: the location of the data directory for this new clone.
:param copy_data: If the data should also be copied (Warning, this is done on the-fly so be sure to unload the core first)
or assure otherwise there's no chance of getting corrupted data (I don't know any other way besides unloading the original code))"""
        try:
            os.makedirs(new_instance_dir)
        except:
            pass
        shutil.copytree(os.path.join(self.instance_dir, 'conf'), os.path.join(new_instance_dir, 'conf'))
        if copy_data:
            shutil.copytree(os.path.join(self.instance_dir, self.data_dir), os.path.join(new_instance_dir, data_dir))
    
    def delete(self, query):
        """Isue a delete command, there's no default query for this to avoid unintentional deletion."""
        self.post(dict(delete=dict(query=query)), auto_list=False)
    
    def _update(self, processors=1, batch_size=1000, start_dir=None, abort_on_error=True, data_types=None, search_dict={}):
        """Refactored method to centralize all ingest methods. 
It allows to ingest file by crawling a subdirectory (start_dir != None) 
or by performing a file system search (data_types != None).
In both cases the ingest will be done either serial (processors=1)
or in parallel (processors >1) with one process handling the search/crawling
and the rest performing the data preparation and ingesting it into Solr."""
        if processors > 1:
            from multiprocessing import Queue
            q = Queue(processors * batch_size)  #just store one extra batch load for every processor
        
        if start_dir is not None and data_types is not None:
            raise Exception("Can't define both a search and a recursive crawling at this time.")
        
        if data_types is not None:
            if processors > 1:
                enqueue_function = enqueue_from_search
                enqueue_args = (q, data_types, search_dict,)
            method_iter = search_iter(data_types,search_dict)
        elif start_dir is not None:
            if processors > 1:
                enqueue_function = enqueue_from_dir
                enqueue_args = (q, start_dir, abort_on_error,)
            method_iter = dir_iter(start_dir, abort_on_error=abort_on_error)
        else:
            raise Exception('Invalid parameters either set start_dir or data_types')
            
        if processors > 1:
            #use one process for generating the file list
            from multiprocessing import Process
            handle_file_init(q, self.core, batch_size=batch_size)
            end_token = '*END-OF-QUEUE*'
            p = Process(target=enqueue_function, args=enqueue_args)
            p.start()

            #the rest for consuming it
            processors -= 1            
            procs = [None]*processors
            for i in range(processors):
                procs[i] = Process(target=handle_file, args=(i,end_token,))
                procs[i].start()
            
            print "Waiting for all processors to finish..."
            p.join()
            print "No more input. Finishing procs."
            handle_file.running = False
            q.put(end_token)
            for i in range(processors):
                procs[i].join()
        else:
            batch_count=0
            batch = []
            for metadata in method_iter:
                #import scipy.io.netcdf
                #with scipy.io.netcdf.netcdf_file(metadata['file'], 'r') as f:
                #    metadata.update(f._attributes)
                ts = os.path.getmtime(metadata['file'])
                metadata['timestamp'] = ts
                metadata['creation_time'] = timestamp_to_solr_date(ts)

                batch.append(metadata)
                if len(batch) >= batch_size:
                    print "Sending entries %s-%s" % (batch_count * batch_size, (batch_count+1) * batch_size)
                    self.post(batch)
                    batch = []
                    batch_count += 1
            
            #flush the batch queue
            if batch:
                print "Sending last %s entries." % (len(batch))
                self.post(batch)
    
    def update_from_search(self, processors=1, batch_size=1000, data_types=None, **search_dict):
        """Updated the Solr index, by ingesting the results obtained from the find_files command.
This is a simple file system search a la find. The search is performed not caring about latest versions
as it makes no sense there.

:param processors: The number of processors to start ingesting. If ==1 then it's run serial, otherwise 1 processor
is used for searching and the rest for preparing and ingesting data.
:param batch_size: The amount of entries that will be sent to Solr on one commit.
:param data_types: The type of data to be ingested. See evaluation_system.model.file.DRSFile.DRS_STRUCTURE 
:param search_dict: All other search parameters."""
        if data_types is None:
            data_types = [REANALYSIS, OBSERVATIONS, BASELINE0, BASELINE1, CMIP5]
        
        self._update(processors=processors, batch_size=batch_size, data_types=data_types, search_dict=search_dict)
    
    def update_from_dir(self, start_dir, abort_on_error=False, processors=1, batch_size=1000,):
        """Updated the Solr index, by ingesting every file found by crawling from start_dir.

:param processors: The number of processors to start ingesting. If ==1 then it's run serial, otherwise 1 processor
is used for searching and the rest for preparing and ingesting data.
:param batch_size: The amount of entries that will be sent to Solr on one commit.
:param start_dir: Root directory to start crawling.
:param abort_on_error: If False then instead of raising an exception print the error and continue."""
        #clean start dir
        start_dir = os.path.abspath(os.path.expandvars(os.path.expanduser(start_dir)))
        self._update(processors=processors, batch_size=batch_size, start_dir=start_dir, abort_on_error=abort_on_error)
    
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
        #metadata['timestamp'] = float(timestamp)
        #metadata['dataset'] = drs_file.to_dataset()
        
        return metadata
    
    def dump(self, dump_file=None, batch_size=1000):
        """Dump a list of files and their timestamps that can be ingested afterwards"""
        if dump_file is None:
            #just to store where and how we are storing this
            dump_file = datetime.now().strftime('/miklip/integration/infrastructure/solr/backup_data/%Y%m%d.csv')
        
        def cache(batch_size):
            offset = 0
            while True:
                url_query = 'select?fl=file,timestamp&start=%s&rows=%s&q=*' % (offset, batch_size)
                print "Calling %s" % url_query
                answer = self.get_json(url_query)
                offset = answer['response']['start']
                total = answer['response']['numFound']
                for item in answer['response']['docs']:
                    yield (item['file'], item['timestamp'],)
                if total - offset <= batch_size:
                    break   #we are done
                else:
                    offset += batch_size
        
        with open(dump_file, 'w') as f:
            for file_path, timestamp in cache(batch_size=batch_size):
                f.write('%s,%s\n' % (file_path, timestamp))
    
    def load(self, dump_file=None, batch_size=1000, abort_on_error=True):
        """Loads a csv as created by dump."""
        if dump_file is None:
            dump_file = datetime.now().strftime('/miklip/integration/infrastructure/solr/backup_data/%Y%m%d.csv')
        
        batch_count=0
        batch = []
        with open(dump_file, 'r') as f:
            for file_path, timestamp in (line.split(',') for line in f):
                try:
                    metadata = SolrCore.to_solr_dict(DRSFile.from_path(file_path))
                    ts = float(timestamp)
                    metadata['timestamp'] = ts
                    metadata['creation_time'] = timestamp_to_solr_date(ts)

                    batch.append(metadata)

                    if len(batch) >= batch_size:
                        print "Sending entries %s-%s" % (batch_count * batch_size, (batch_count+1) * batch_size)
                        self.post(batch)
                        batch = []
                        batch_count += 1
                    
                except:
                    print "Can't ingest file %s" % file_path
                    if abort_on_error: raise
        
        #flush the batch queue
        if batch:
            print "Sending last %s entries." % (len(batch))
            self.post(batch)

def timestamp_to_solr_date(timestamp):
    """Transform a timestamp (float) into a string parseable by Solr"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')

#-- These are for multiple processes... 
#but There's no benefit for having multiple threads at this time
#on the contrary, it's worse :-/
#There's no improvement for not having this construct either, so I'm leaving it
#here. It might help in the future...
def search_iter(data_types, search_dict):
    if not isinstance(data_types, list): 
        data_types = [ data_types]
    for data_type in data_types:
        for drs_file in DRSFile.search(data_type, latest_version=False, **search_dict):
            yield SolrCore.to_solr_dict(drs_file)

def dir_iter(start_dir, abort_on_error=True):
    for base_dir, _, files in os.walk(start_dir):
        try:
            for f in files:
                path = os.path.join(base_dir,f)
                yield SolrCore.to_solr_dict(DRSFile.from_path(path))
        except:
            print "Can't ingest file %s" % path
            if abort_on_error: raise
def enqueue_from_search(q, data_types, search_dir):
    for metadata in search_iter(data_types, search_dir):
        q.put(metadata)
def enqueue_from_dir(q, start_dir, abort_on_error=True):
    for metadata in dir_iter(start_dir, abort_on_error=abort_on_error):
        q.put(metadata)

def handle_file_init(q, core, batch_size=100):
    handle_file.batch_size = batch_size
    handle_file.running = True
    handle_file.q = q
    handle_file.core = core

def handle_file(number, end_token):
    print "starting proc %s" % number
    batch_count=0
    batch = []
    solr = SolrCore(core=handle_file.core)
    while handle_file.running:
        value = handle_file.q.get()
        if value == end_token:
            handle_file.q.put(end_token)
            break
        #import scipy.io.netcdf
        #with scipy.io.netcdf.netcdf_file(value['file'], 'r') as f:
        #    value.update(f._attributes)
        ts = os.path.getmtime(value['file'])
        value['timestamp'] = ts
        value['creation_time'] = timestamp_to_solr_date(ts)
        batch.append(value)
        if len(batch) >= handle_file.batch_size:
            print "Sending entries %s-%s from %s" % (batch_count * handle_file.batch_size, (batch_count+1) * handle_file.batch_size, number)
            solr.post(batch)
            batch = []
            batch_count += 1
        
    if batch:
        print "Sending last %s entries from %s." % (len(batch), number)
        solr.post(batch)
    print "proc %s done!" % number


