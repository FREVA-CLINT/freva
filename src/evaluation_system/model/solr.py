'''
Created on 11.03.2013

@author: estani

This package encapsulate access to a solr instance
'''

import os
import urllib2, urllib
import json

from evaluation_system.model.file import DRSFile, BASELINE0, BASELINE1, CMIP5, OBSERVATIONS, REANALYSIS




class SolrFindFiles(object):
    """Encapsulate access to Solr for the find files command"""
    solr_url = 'http://localhost:8983/solr'
    
    def __init__(self, solr_url=None, core='files'):
        """Create the connection pointing to the proper solr url and core"""
        if solr_url:
            self.solr_url = solr_url
        self.core_url = self.solr_url + '/' + core
    
    def post(self, list_of_dicts, auto_list=True):
        """Sends some json to Solr"""
        if auto_list and not isinstance(list_of_dicts, list): list_of_dicts=[list_of_dicts]

        req=urllib2.Request(self.core_url + '/update/json?commit=true', json.dumps(list_of_dicts))
        req.add_header("Content-type", "application/json")
        
        return urllib2.urlopen(req).read()
    
    def get_json(self, endpoint, raw_endpoint=False):
        """Return some json from server"""
        if raw_endpoint:
            req=urllib2.Request(self.solr_url + endpoint)    
        else:
            req=urllib2.Request(self.core_url + endpoint)    
        
        return json.loads(urllib2.urlopen(req).read())
    
    def get_solr_fields(self):
        """Return information about the Solr fields"""
        if not self._fields:
            self._fields = self.get_json(self.core_url + '/admin/luke?wt=json')['fields']
        return self._fields
    
    def delete(self, query='*:*'):
        """Wipes out the complete Solr index"""
        self.post(dict(delete=dict(query=query)), auto_list=False)
    
    def update(self, data_types=None, processors=1, batch_size=1000):
        """Updated the Solr index, by ingesting every file in to it"""
        if data_types is None:
            data_types = [REANALYSIS, OBSERVATIONS, BASELINE0, BASELINE1, CMIP5]

        from multiprocessing import Queue, Process
        q = Queue(processors * batch_size)  #just store one extra batch load for every processor
        handle_file_init(q, batch_size=batch_size)
        end_token = '*END-OF-QUEUE*'
        p = Process(target=find_files, args=(q,data_types,))
        p.start()

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

    def to_solr_query(self, partial_dict):
        params = []
        for key, value in partial_dict.items():
            if key.endswith('_not_'):
                #handle negation
                key = '-' + key[:-5]
            if isinstance(value, list):
                #implies an or
                constraint = ' OR '.join(['%s:%s' % (key,v) for v in value])
            else:
                constraint = '%s:%s' % (key, value)
            params.append(('fq', constraint,))
        return urllib.urlencode(params)
        

    def _search(self, **partial_dict):
        batch_size = 100
        offset = 0
        query = SolrFindFiles.to_solr_query(partial_dict)
        while True:
            answer = self.get_json('/select?wt=json&fl=file&start=%s&rows=%s&%s' % (offset, batch_size, query))
            offset = answer['response']['start']
            total = answer['response']['numFound']
            for item in answer['response']['docs']:
                yield item['file']
            
            if total - offset <= batch_size:
                break   #we are done
            else:
                offset += batch_size
        
    @staticmethod
    def search (**partial_dict):
        #use default
        s = SolrFindFiles()
        return s._search(partial_dict)

    @staticmethod
    def to_solr_dict(drs_file):
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
        if dump_file is None:
            from datetime import datetime
            #just to store where and how we are storing this
            dump_file = datetime.now().strftime('/miklip/integration/infrastructure/solr/backup_data/%Y%m%d.csv')

        def cache(batch_size):
            offset = 0
            while True:
                url_query = '/select?wt=json&fl=file,timestamp&start=%s&rows=%s&q=*' % (offset, batch_size)
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
        if dump_file is None:
            from datetime import datetime
            dump_file = datetime.now().strftime('/miklip/integration/infrastructure/solr/backup_data/%Y%m%d.csv')

        batch_count=0
        batch = []
        with open(dump_file, 'r') as f:
            for file_path, timestamp in (line.split(',') for line in f):
                try:
                    metadata = SolrFindFiles.to_solr_dict(DRSFile.from_path(file_path))
                    metadata['timestamp'] = float(timestamp)
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

#-- These are for multiple processes... 
#but There's no benefit for having multiple threads at this time
#on the contrary, it's worse :-/
#There's no improvement for not having this construct either, so I'm leaving it
#here. It might help in the future...
def find_files(q, data_types):
    if not isinstance(data_types, list): 
        data_types = [ data_types]
    for data_type in data_types:
        for drs_file in DRSFile.search(data_type, latest_version=False):
            q.put(SolrFindFiles.to_solr_dict(drs_file))

def handle_file_init(q, batch_size=100):
    handle_file.batch_size = batch_size
    handle_file.running = True
    handle_file.q = q

def handle_file(number, end_token):
    print "starting proc %s" % number
    batch_count=1
    batch = []
    solr = SolrFindFiles()
    while handle_file.running:
        value = handle_file.q.get()
        if value == end_token:
            handle_file.q.put(end_token)
            break
        #import scipy.io.netcdf
        #with scipy.io.netcdf.netcdf_file(value['file'], 'r') as f:
        #    value.update(f._attributes)
        value['timestamp'] = os.path.getmtime(value['file'])
        batch.append(value)
        if len(batch) >= handle_file.batch_size:
            print "Sending Entry %s from %s" % (batch_count * handle_file.batch_size, number)
            solr.post(batch)
            batch = []
            batch_count += 1
        
    if batch:
        solr.post(batch)
    print "proc %s done!" % number


