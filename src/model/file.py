'''
Created on 20.09.2012

@author: estani
'''
import json
import glob

class BaselineFile(object):
    BASELINE = [
        #baseline 0 data      
        {
        "root_dir":"/gpfs_750/projects/CMIP5/data/",
        "parts_dir":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable/file_name".split('/'),
        "parts_dataset":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble".split('/'),
        "parts_versioned_dataset":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version".split('/'),
        "parts_file_name":"variable-cmor_table-model-experiment-ensemble-time".split('-'),
        "parts_time":"start_time-end_time",
        "defaults" : {"project":"cmip5", "institute":"MPI-M", "model":"MPI-ESM-LR"}
        }]

    def __init__(self, file_dict=None, baseline_nr=0):
        self.baseline_nr = baseline_nr
        if not file_dict: file_dict = {} 
        self.dict = file_dict  
        
    def __repr__(self):
        """returns the json representation of this object that can be use to create a copy."""
        return self.to_json()
    
    def __str__(self):
        """The string representation is the absolute path to the file."""
        return self.to_path()

    def to_json(self):
        return json.dumps(self.dict)
    
    def to_path(self):
        #TODO: check if construction is complete and therefore can succeed
        result = [self.dict['root_dir']]
        for key in self.get_baseline()['parts_dir']:
            result.append(self.dict['parts'][key])
        return '/'.join(result).replace('//', '/')
    
    def to_dataset(self, versioned=False):
        """Extract the dataset name (DRS) from the path"""
        result = []
        if versioned:
            if not self.is_versioned():
                raise Exception('baseline %s is not versioned!' % self.baseline_nr)
            iter_parts = self.get_baseline()['parts_versioned_dataset']
        else:  
            iter_parts = self.get_baseline()['parts_dataset']
            
        for key in iter_parts:
            result.append(self.dict['parts'][key])
        return '.'.join(result)
    
    def is_versioned(self):
        """If this baseline versions files"""
        return 'parts_versioned_dataset' in self.get_baseline()
    
    def get_version(self):
        """Return the *dataset* version from which this file is part of.
        Returns None if the dataset is not versioned"""
        if 'version' in self.dict:
            return self.dict['version']
        else:
            return None
        
    
    @staticmethod
    def from_path(path, baseline_nr=0):
        
        bl = BaselineFile._get_baseline(baseline_nr)
    
    
        #trim root_dir
        if not path.startswith(bl['root_dir']):
            raise Exception("This file does not correspond to baseline %s" % baseline_nr)                                                         
        
        parts = path[len(bl['root_dir']):].split('/')
        
        #check the number of parts
        if len(parts) != len(bl['parts_dir']):
            raise Exception("Can't parse this path. Expected %d elements but got %d." % (len(bl['parts_dir']), len(parts)))
        
        #first the dir
        result = {}
        result['root_dir'] = bl['root_dir']
        result['parts'] = {}
        for i in range(len(bl['parts_dir'])):
            result['parts'][bl['parts_dir'][i]] = parts[i]
        
        #split file name
        ##(extract .nc before splitting)
        parts = result['parts']['file_name'][:-3].split('_')
        for i in range(len(bl['parts_file_name'])):
            result['parts'][bl['parts_file_name'][i]] = parts[i]
        
        bl_file = BaselineFile(result, baseline_nr=baseline_nr)
        
        return bl_file
    
    def get_baseline(self):
        return BaselineFile._get_baseline(self.baseline_nr)
    
    @staticmethod
    def _get_baseline(baseline_nr):
        """Returns the Object representing the baseline given.
        Throws an exception if there's no such baseline implemented.
        (NOTE: baseline refers to the different states of data for comparison in the MiKlip project"""
        if baseline_nr < 0 or baseline_nr > len(BaselineFile.BASELINE) - 1:
            raise Exception("Baseline %s not implemented yet." % baseline_nr)
        return BaselineFile.BASELINE[baseline_nr]
    
    @staticmethod
    def from_dict(file_dict, baseline_nr=0):
        #need to check file_dict is as expected...
        #if 'baseline_nr' in file_dict:
        #    baseline_nr = file_dict['baseline_nr']
        #    del file_dict['baseline_nr']
        return BaselineFile(file_dict, baseline_nr=baseline_nr)
        
    @staticmethod
    def from_json(json_str, baseline_nr=0):
        return BaselineFile.from_dict(json.loads(json_str), baseline_nr=baseline_nr)
    
    @staticmethod
    def search(baseline_nr=0, latest_version=True, **partial_dict):
        """Search for files from the given parameters as part of the baseline names.
        returns := list of Matching Baseline files"""
        bl = BaselineFile._get_baseline(baseline_nr)
        search_dict = bl['defaults'].copy()
        search_dict.update(partial_dict)
        
        result = [bl['root_dir']]
        for key in BaselineFile._get_baseline(baseline_nr)['parts_dir']:
            if key in search_dict:
                result.append(search_dict[key])
            else:
                result.append("*")
        
        local_path = '/'.join(result).replace('//', '/')
        bl_files = []
        for path in glob.glob(local_path):
            bl_files.append(BaselineFile.from_path(path, baseline_nr))
        
        if latest_version:
            datasets = {}
            for blf in bl_files:
                ds = blf.to_dataset(versioned=False)
                if ds in datasets:
                    if datasets[ds].get_version() > blf.get_version(): continue
                datasets[ds] = blf
            bl_files = datasets.values()
        
        return bl_files
