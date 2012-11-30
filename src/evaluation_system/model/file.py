'''
Created on 20.09.2012

@author: estani
'''
import json
import glob
import os
import logging
log = logging.getLogger(__name__)

BASELINE0 = 'baseline 0'
BASELINE1 = 'baseline 1'
OBSERVATIONS = 'observations'
REANALYSIS = 'reanalysis'
class DRSFile(object):
    
    DRS_STRUCTURE = {
        #baseline 0 data      
        BASELINE0 : {
         "root_dir":"/gpfs_750/projects/CMIP5/data",
         "parts_dir":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable/file_name".split('/'),
         "parts_dataset":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble".split('/'),
         "parts_versioned_dataset":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version".split('/'),
         "parts_file_name":"variable-cmor_table-model-experiment-ensemble-time".split('-'),
         "parts_time":"start_time-end_time",
         "defaults" : {"project":"cmip5", "institute":"MPI-M", "model":"MPI-ESM-LR"}
        },
        #baseline 1 data
        BASELINE1 : {
         "root_dir":"/miklip/global/prod/archive",
         "parts_dir":"project/product/institute/model/experiment/time_frequency/realm/variable/ensemble/file_name".split('/'),
         "parts_dataset":"project.product.institute.model.experiment.time_frequency.realm.variable.ensemble".split('.'),
         "parts_file_name":"variable-model-experiment-ensemble-time".split('-'),
         "parts_time":"start_time-end_time",
         "defaults" : {"project":"baseline1", "product":"output", "institute":"MPI-M", "model":"MPI-ESM-LR"}
         },
         OBSERVATIONS : {
         "root_dir":"/miklip/integration/data4miklip",
         "parts_dir":"product/realm/variable/time_frequency/data_structure/institute/source/version/file_name".split('/'),
         "parts_dataset":"project.institute.source.time_frequency".split('.'),
         "parts_versioned_dataset":"project.institute.source.time_frequency.version".split('.'),
         "parts_file_name":"variable-source-level-time".split('-'),
         "parts_time":"start_time-end_time",
         "defaults" : {"project":"obs4MIPS", "product":"observations", "data_structure":"grid"}
         },
         REANALYSIS : {
         "root_dir":"/miklip/integration/data4miklip",
         "parts_dir":"product/institute/model/experiment/time_frequency/realm/variable/file_name".split('/'),
         "parts_dataset":"project.institute.experiment.realm.time_frequency".split('.'),
         "parts_versioned_dataset":"project.institute.experiment.realm.time_frequency.version".split('.'),
         "parts_file_name":"variable-table-product-experiment-time".split('-'),
         "parts_time":"start_time-end_time",
         "defaults" : {"project":"ana4MIPS", "product":"reanalysis"}
        },
        }

    def __init__(self, file_dict=None, drs_structure=BASELINE0):
        self.drs_structure = drs_structure
        if not file_dict: file_dict = {} 
        self.dict = file_dict
        #trim the last slash if present in root_dir
        if 'root_dir' in self.dict and self.dict['root_dir'][-1] == '/':
            self.dict['root_dir'] = self.dict['root_dir'][:-1]
        
        
    def __repr__(self):
        """returns the json representation of this object that can be use to create a copy."""
        return self.to_json()
    
    def __str__(self):
        """The string representation is the absolute path to the file."""
        return self.to_path()
    
    def __cmp__(self, other):
        if isinstance(other, DRSFile):
            return cmp(self.to_path(), other.to_path())
        return -1

    def to_json(self):
        return json.dumps(self.dict)
    
    def to_path(self):
        #TODO: check if construction is complete and therefore can succeed
        result = self.dict['root_dir']
        for key in self.get_baseline()['parts_dir']:
            result = os.path.join(result, self.dict['parts'][key])
        return result
    
    def to_dataset(self, versioned=False):
        """Extract the dataset name (DRS) from the path"""
        result = []
        if versioned:
            if not self.is_versioned():
                raise Exception('%s is not versioned!' % self.drs_structure)
            iter_parts = self.get_baseline()['parts_versioned_dataset']
        else:  
            iter_parts = self.get_baseline()['parts_dataset']
            
        for key in iter_parts:
            if key in self.dict['parts']:
                result.append(self.dict['parts'][key])
            elif key in self.get_baseline()['defaults']:
                result.append(self.get_baseline()['defaults'][key])
        return '.'.join(result)
    
    def is_versioned(self):
        """If this baseline versions files"""
        return 'parts_versioned_dataset' in self.get_baseline()
    
    def get_version(self):
        """Return the *dataset* version from which this file is part of.
        Returns None if the dataset is not versioned"""
        if 'version' in self.dict['parts']:
            return self.dict['parts']['version']
        else:
            return None
        
    
    @staticmethod
    def from_path(path, drs_structure=BASELINE0):
        path = os.path.realpath(path)
        bl = DRSFile._get_baseline(drs_structure)
    
        #trim root_dir
        if not path.startswith(bl['root_dir'] + '/'):
            raise Exception("This file does not correspond to %s" % drs_structure)                                                         
        
        parts = path[len(bl['root_dir'])+1:].split('/')
        
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
        if len(parts) == len( bl['parts_file_name']) - 1 \
            and 'r0i0p0' in parts :
            #no time
            parts.append(None)
            
        log.debug("Path: %s\nFile_parts:%s\ndrs_structure_parts:%s", path, parts, bl['parts_file_name'])
        for i in range(len(bl['parts_file_name'])):
            result['parts'][bl['parts_file_name'][i]] = parts[i]
        
        bl_file = DRSFile(result, drs_structure=drs_structure)
        
        return bl_file
    
    def get_baseline(self):
        return DRSFile._get_baseline(self.drs_structure)
    
    @staticmethod
    def _get_baseline(drs_structure=BASELINE0):
        """Returns the Object representing the baseline given.
        Throws an exception if there's no such baseline implemented.
        (NOTE: baseline refers to the different states of data for comparison in the MiKlip project"""
        if drs_structure not in DRSFile.DRS_STRUCTURE:
            raise Exception("Unknown DRS structure %s" % drs_structure)
        return DRSFile.DRS_STRUCTURE[drs_structure]
    
    @staticmethod
    def from_dict(file_dict, drs_structure=BASELINE0):
        #need to check file_dict is as expected...
        #if 'baseline_nr' in file_dict:
        #    baseline_nr = file_dict['baseline_nr']
        #    del file_dict['baseline_nr']
        return DRSFile(file_dict, drs_structure=drs_structure)
        
    @staticmethod
    def from_json(json_str, drs_structure=BASELINE0):
        return DRSFile.from_dict(json.loads(json_str), drs_structure=drs_structure)
    
    @staticmethod
    def search(drs_structure=BASELINE0, latest_version=True, **partial_dict):
        """Search for files from the given parameters as part of the baseline names.
        returns := Generator returning matching Baseline files"""
        
        bl = DRSFile._get_baseline(drs_structure)
        search_dict = bl['defaults'].copy()
        search_dict.update(partial_dict)
        
        #only baseline 0 is versioned
        if latest_version and ('parts_versioned_dataset' not in bl):
            latest_version = False
            log.error("No version information stored in structure thus latest version is inactive.")

        local_path = bl['root_dir']
        for key in bl['parts_dir']:
            if key in search_dict:
                local_path = os.path.join(local_path, search_dict[key])
                del search_dict[key]    #remove it so we can see if all keys matched
            else:
                local_path = os.path.join(local_path, "*")
        
        #NOTE: We might have defaults for the datasets that are not appearing in the directories.
        if set(search_dict) - set(bl['defaults']):
            #ok, there are typos or non existing constraints in the search.
            #which are not in the defaults. Those are "strange" to the selected structure.
            log.warn("There where unused constraints: %s\nFor %s try one of: %s\n" % 
                             (','.join(search_dict), drs_structure, ','.join(bl['parts_dir'])))
            raise Exception("Unknown parameter(s) %s" % 
                            (','.join(search_dict)))
        #if the latest version is not required we may use a generator and yield a value as soon as it is found
        #If not we need to parse all until we can give the results out. We are not storing more than the latest
        #version, but if we could assure a certain order we return values as soon as we are done with a dataset
        datasets = {}
        for path in glob.iglob(local_path):
            blf = DRSFile.from_path(path, drs_structure)
            if not latest_version:
                yield blf
            else:
                #if not we need to check if the corresponding dataset version is recent
                ds = blf.to_dataset(versioned=False)
                if ds not in datasets or datasets[ds][0].get_version() < blf.get_version():
                    #if none or a newer version is found, reinit the dataset list
                    datasets[ds] = [blf]
                elif datasets[ds][0].get_version() == blf.get_version():
                    #if same version, add to previous (we are gathering multiple files per dataset) 
                    datasets[ds].append(blf)
                
        if latest_version:
            #then return the results stored in datasets
            for latest_version_file in [v for sub in datasets.values() for v in sub]:
                yield latest_version_file
