'''
Created on 11.03.2013

@author: estani

This package encapsulate access to a solr instance
'''

import os
import urllib2
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
    
    def get_json(self, endpoint):
        """Return some json from server"""
        req=urllib2.Request(self.solr_url + endpoint)    
        
        return json.loads(urllib2.urlopen(req).read())
    
    def get_solr_fields(self):
        """Return information about the Solr fields"""
        if not self._fields:
            self._fields = self.get_json(self.core_url + '/admin/luke?wt=json')['fields']
        return self._fields
    
    def wipe_out(self):
        """Wipes out the complete Solr index"""
        self.post(dict(delete=dict(query="*:*")), auto_list=False)
    
    def update(self, data_types=None, processors=5):
        """Updated the Solr index, by ingesting every file in to it"""
        if data_types is None:
            data_types = [REANALYSIS, OBSERVATIONS, BASELINE0, BASELINE1, CMIP5]

        from multiprocessing import Queue, Process
        q = Queue(1000)
        handle_file_init(q, batch_size=500)
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


def find_files(q, data_types):
    if not isinstance(data_types, list): 
        data_types = [ data_types]
    for data_type in data_types:
        for nc_file in DRSFile.search(data_type, latest_version=False):
            metadata = nc_file.dict['parts'].copy()
            metadata['data_type'] = data_type
            metadata['file'] = nc_file.to_path()
            #don't do this now, this takes a while
            #metadata['timestamp'] = os.path.getmtime(nc_file.to_path())
            q.put(metadata)

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


