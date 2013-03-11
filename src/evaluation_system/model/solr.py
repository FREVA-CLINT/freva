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
    
    def update(self):
        """Updated the Solr index, by ingesting every file in to it"""
        batch_count=1
        batch_size = 100
        batch = []
        for data_type in [REANALYSIS, OBSERVATIONS, BASELINE0, BASELINE1, CMIP5]:
            for nc_file in DRSFile.search(data_type):
                
                metadata = nc_file.dict['parts'].copy()
                metadata['file'] = nc_file.to_path()
                metadata['timestamp'] = os.path.getmtime(nc_file.to_path())
                batch.append(metadata)
                if len(batch) >= batch_size:
                    print "Sending batch %s" % batch_count
                    self.post(batch)
                    batch = []
                    batch_count += 1
        
        if batch:
            self.post(batch)
            batch = []




