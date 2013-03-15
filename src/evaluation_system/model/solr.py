'''
Created on 11.03.2013

@author: estani

This package encapsulate access to a solr instance
'''

import urllib

from evaluation_system.model.solr_core import SolrCore


class SolrFindFiles(object):
    """Encapsulate access to Solr like the find files command"""
    def __init__(self, core=None, host=None, port=None):
        """Create the connection pointing to the proper solr url and core. 
The default values of these parameters are setup in evaluation_system.model.solr_core.SolrCore
and read from the configuration file."""
        self.solr = SolrCore(core, host=host, port=port)
    
    def to_solr_query(self, partial_dict):
        """Creates a Solr query assuming the default operator is "AND". See schema.xml for that."""
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
    
    def _search(self, batch_size=1000, latest_version=True, **partial_dict):
        offset = 0
        if 'free_text' in partial_dict:
            free_text = partial_dict.pop('free_text')
        elif 'q' in partial_dict:
            free_text = partial_dict.pop('q')
        else:
            free_text='*:*'
            
        query = self.to_solr_query(partial_dict)
        query += '&q=%s' % free_text
        
        if latest_version:
            query += '&group=true&group.field=file_no_version&group.sort=version+desc&group.ngroups=true&group.format=simple'
            
            while True:
                answer = self.solr.get_json('select?fl=file&start=%s&rows=%s&%s' % (offset, batch_size, query))
                offset = answer['grouped']['file_no_version']['doclist']['start']
                total = answer['grouped']['file_no_version']['ngroups']
                for item in answer['grouped']['file_no_version']['doclist']['docs']:
                    yield item['file']
            
                if total - offset <= batch_size:
                    break   #we are done
                else:
                    offset += batch_size
            
        else:    
            while True:
                answer = self.solr.get_json('select?fl=file&start=%s&rows=%s&%s' % (offset, batch_size, query))
                offset = answer['response']['start']
                total = answer['response']['numFound']
                for item in answer['response']['docs']:
                    yield item['file']
            
                if total - offset <= batch_size:
                    break   #we are done
                else:
                    offset += batch_size
        
    @staticmethod
    def search (batch_size=1000, latest_version=True, **partial_dict):
        #use default
        s = SolrFindFiles()
        return s._search(batch_size=batch_size, latest_version=latest_version, **partial_dict)

