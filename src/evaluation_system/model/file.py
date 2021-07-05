"""
.. moduleauthor:: christopher kadow / Sebastian Illing
.. first version written by estanislao gonzalez

The module encapsulates all methods for accessing files on the system.
These are mainly model and observational and reanalysis data.
"""
import json
import glob
from pathlib import Path
import os
import logging
from evaluation_system.misc.utils import find_similar_words
log = logging.getLogger(__name__)


CMIP5 = 'cmip5'
"""DRS structure for CMIP5 Data"""
BASELINE0 = 'baseline0'
"""DRS structure for Baseline 0 Data (it's a subset of CMIP5 data)"""
OBSERVATIONS = 'observations'
"""DRS structure for observational data."""
REANALYSIS = 'reanalysis'
"""CMOR structure for reanalysis data."""
CRAWLMYDATA = 'crawl_my_data'
"""CMOR structure for user data."""

class DRSFile(object):
    """Represents a file that follows the
    DRS <http://cmip-pcmdi.llnl.gov/cmip5/docs/cmip5_data_reference_syntax.pdf> standard."""
    # Lazy initialized in find_structure_from_path
    DRS_STRUCTURE_PATH_TYPE = None
    DRS_STRUCTURE = {
        # cmip5 data
        CMIP5: {
         "root_dir": "/mnt/data4freva/model/global",
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable/file_name".split('/'),
         "parts_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble//variable".split('/'),
         "parts_versioned_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable".split('/'),
         "parts_file_name": "variable-cmor_table-model-experiment-ensemble-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": CMIP5,
         "defaults": {"project": "cmip5" }
         },
        # observations
         OBSERVATIONS: {
         "root_dir": "/mnt/data4freva",
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable/file_name".split('/'),
         "parts_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble//variable".split('/'),
         "parts_versioned_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable".split('/'),
         "parts_file_name": "variable-experiment-level-version-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": OBSERVATIONS,
         "defaults": {"project": "observations"}
         },
         REANALYSIS : {
         "root_dir": "/mnt/data4freva",
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/variable/ensemble/file_name".split('/'),
         "parts_dataset": "project/product/institute/model/experiment/time_frequency/realm/variable".split('/'),
         "parts_file_name": "variable-cmor_table-project-experiment-ensemble-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": REANALYSIS,
         "defaults": {"project": "reanalysis", "product": "reanalysis"}
        },
         CRAWLMYDATA : {
         "root_dir": str(Path('~/data4freva').expanduser()),
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/variable/ensemble/file_name".split('/'),
         "parts_dataset": "project.product.institute.model.experiment.time_frequency.realm.variable.ensemble".split('.'),
         "parts_file_name": "variable-cmor_table-model-experiment-ensemble-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": CRAWLMYDATA,
         "defaults": {}
         },
         # ADDMORE
 
             }   
    """Describes the DRS structure of different types of data. The key values of this dictionary are:

root_dir
    Directory from where this files are to be found

parts_dir
    list of subdirectory category names the values they refer to (e.g. ['model', 'experiment'])

parts_dataset
    The components of a dataset name (this data should also be found in parts_dir)

parts_versioned_dataset (optional)
    If this datasets are versioned then define the version structure of them (i.e. include the version number in the dataset name)

parts_file_name
    elements composing the file name (no ".nc" though)

data_type
    same value as this key structure (for reverse traverse)

defaults
    list with values that "shouldn't" be required to be changed (e.g. for observations, project=obs4MIPS)
"""
    def __init__(self, file_dict=None, drs_structure=BASELINE0):
        """Creates a DRSfile out of the dictionary containing information about the file or from scratch.

:param file_dict: dictionary with the DRS component values and keys from which this file will be initialized. 
:param drs_structure: Which structure is going to be used with this file.
:type drs_structure: key value of :class:`DRSFile.DRS_STRUCTURE` 
"""
        self.drs_structure = drs_structure
        if not file_dict:
            file_dict = {}
        self.dict = file_dict
        # trim the last slash if present in root_dir
        if 'root_dir' in self.dict and self.dict['root_dir'][-1] == '/':
            self.dict['root_dir'] = self.dict['root_dir'][:-1]

    def __repr__(self):  # pragma nocover
        """returns the json representation of this object that can be use to create a copy."""
        return self.to_json()

    def __str__(self):  # pragma nocover
        """The string representation is the absolute path to the file."""
        return self.to_path()

    def __cmp__(self, other):
        if isinstance(other, DRSFile):
            return cmp(self.to_path(), other.to_path())
        return -1

    def to_json(self):
        """:returns: (str) the json representation of the dictionary encapsulating the DRS components of this file."""
        return json.dumps(self.dict)

    def to_path(self):
        """:returns: (str) the path to the file as described by the DRS components. The file is not required to exist.
:raises: KeyError if can't construct the path because there's information missing in the DRS components."""
        # TODO: check if construction is complete and therefore can succeed
        result = self.dict['root_dir']
        for key in self.getDrsStructure()['parts_dir']:
            if key not in self.dict['parts']:
                raise KeyError("Can't construct path as key %s is missing." % key)
            result = os.path.join(result, self.dict['parts'][key])
        return result

    def to_dataset(self, versioned=False, to_path=False):
        """creates the dataset to which this file is part of out of the DRS information.

:param versioned: If the dataset should contain information about the version. Note that not
                  all DRS structures are versioned, so in those cases where there is just no
                  version information this makes no difference.
:type versioned: bool
:param to_path: if true return the path to the dataset, otherwise returns the dataset identifier."""
        result = []
        if versioned:
            if not self.is_versioned():
                raise Exception('%s is not versioned!' % self.drs_structure)
            iter_parts = self.getDrsStructure()['parts_versioned_dataset']
        else:
            iter_parts = self.getDrsStructure()['parts_dataset']

        for key in iter_parts:
            if key in self.dict['parts']:
                result.append(self.dict['parts'][key])
            elif key in self.getDrsStructure()['defaults']:
                result.append(self.getDrsStructure()['defaults'][key])
        if to_path:
            return self.getDrsStructure()['root_dir'] + '/' + '/'.join(result)
        else:
            return '.'.join(result)

    def to_dataset_path(self, versioned=False):
        """returns the path to the current dataset. Commodity method for to_dataset.
We are assuming the dataset is a sub-path of all files in it.

:param versioned: If the dataset should contain information about the version. Note that not
                  all DRS structures are versioned, so in those cases where there is just no
                  version information this makes no difference.
:type versioned: bool"""
        return self.to_dataset(versioned=versioned, to_path=True)

    def is_versioned(self):
        """If this file is from a DRS structure that is versioned."""
        return 'parts_versioned_dataset' in self.getDrsStructure()

    def get_version(self):
        """
:returns: the *dataset* version from which this file is part of or None if the dataset is not versioned.
          Note that this is the version of the dataset and not of the file, since the DRS does not version
          files but datasets.
:rtype: int"""
        if 'version' in self.dict['parts']:
            return self.dict['parts']['version']
        else:
            return None

    @staticmethod
    def _get_structure_prefix_map():
        """:returns: reversed map root_path->drs_struct_name (lazy initialized)."""

        if DRSFile.DRS_STRUCTURE_PATH_TYPE is None:
            DRSFile.DRS_STRUCTURE_PATH_TYPE = {}
            for st_type in DRSFile.DRS_STRUCTURE:
                path_prefix = DRSFile.DRS_STRUCTURE[st_type]['root_dir']
                for part in DRSFile.DRS_STRUCTURE[st_type]['parts_dir']:
                    # if we have more info use it to generate a unique root path
                    # (e.g. cmip5 and baseline0 or baseline1 share the same root path!)
                    if part in DRSFile.DRS_STRUCTURE[st_type]['defaults'] and \
                            all([char not in DRSFile.DRS_STRUCTURE[st_type]['defaults'][part] for char in '*?']):
                        # but only use it if it's a plain string, no globing.
                        path_prefix += '/' + DRSFile.DRS_STRUCTURE[st_type]['defaults'][part]
                    else:
                        break
                DRSFile.DRS_STRUCTURE_PATH_TYPE[path_prefix] = st_type
        return DRSFile.DRS_STRUCTURE_PATH_TYPE

    @staticmethod
    def find_structure_from_path(file_path, allow_multiples=False):
        """Return all DRS structures that might be applicable to the given path.
This is resolved by checking if the prefix of any structure paths matches that
of the given file path.

:param file_path: full path to a file, whose drs structure is being searched for.
:param allow_multiples: if true returns a list with all possible structures, otherwise returns the first match found.
:returns: the name of the drs struct(s) that can be used to parse this path. The parsing is not done, so
 it might still fail. It just guarantees that if any, only the structures returned here *might* work."""
        structures = []
        for path_prefix, st_type in DRSFile._get_structure_prefix_map().items():
            if file_path.startswith(path_prefix):
                if allow_multiples:
                    structures.append(st_type)
                else:
                    return st_type
        if not structures:
            raise Exception("Unrecognized DRS structure in path %s" % file_path)
        else:
            return structures

    @staticmethod
    def find_structure_in_path(dir_path, allow_multiples=False):
        """Return all DRS structures that might be applicable to the given directory path.
This is resolved by checking if the given path is contained within any drs structure. It's used while crawling.

:param dir_path: path a directory, who might contain drs conform files.
:param allow_multiples: if true returns a list with all possible structures, otherwise returns the first match found.
:returns: the name of the drs struct(s) that can be used to find files within the given dir_path."""
        structures = []
        for path_prefix, st_type in DRSFile._get_structure_prefix_map().items():
            if path_prefix.startswith(dir_path):
                if allow_multiples:
                    structures.append(st_type)
                else:
                    return st_type
        if not structures:
            raise Exception("No DRS structure found in %s." % dir_path)
        else:
            return structures

    @staticmethod
    def from_path(path, drs_structure=None):
        """Extract a DRSFile object out of a path.
:param path: path to a file that is part of the ``drs_structure``.
:type param: str
:param drs_structure: Which structure is going to be used with this file.
:type drs_structure: key value of :class:`DRSFile.DRS_STRUCTURE`
"""
        if drs_structure is None:
            drs_structure = DRSFile.find_structure_from_path(path)
        path = os.path.abspath(path)
        bl = DRSFile._getDrsStructure(drs_structure)

        # trim root_dir
        if not path.startswith(bl['root_dir'] + '/'):
            raise Exception("File %s does not correspond to %s" % (path, drs_structure))

        parts = path[len(bl['root_dir'])+1:].split('/')

        # check the number of parts
        if len(parts) != len(bl['parts_dir']):
            raise Exception("Can't parse this path. Expected %d elements but got %d." % (len(bl['parts_dir']), len(parts)))

        # first the dir
        result = {}
        result['root_dir'] = bl['root_dir']
        result['parts'] = {}
        for i in range(len(bl['parts_dir'])):
            result['parts'][bl['parts_dir'][i]] = parts[i]

        # split file name
        # (extract .nc before splitting)
        parts = result['parts']['file_name'][:-3].split('_')
        if len(parts) == len(bl['parts_file_name']) - 1 \
            and 'fx' in parts:
            # no time
            parts.append(None)

        try:
            for i in range(len(bl['parts_file_name'])):
                if bl['parts_file_name'][i] not in result['parts']:
                    result['parts'][bl['parts_file_name'][i]] = parts[i]

        except IndexError:
            raise Exception("File %s does not follow the expected naming scheme for %s" % (path, drs_structure))

        bl_file = DRSFile(result, drs_structure=drs_structure)

        return bl_file

    def getDrsStructure(self):
        """:returns: the :class:`DRSFile.DRS_STRUCTURE` used by this file."""
        return DRSFile._getDrsStructure(self.drs_structure)

    @staticmethod
    def _getDrsStructure(drs_structure=BASELINE0):
        """
:param drs_structure: name of a DRS structure (key of :class:`DRSFile.DRS_STRUCTURE`)
:type drs_structure: str
:returns: (dict) the dictionary of the DRS structure of the requested type.
:raises: Exception if there's no such DRS structure.
"""
        if drs_structure not in DRSFile.DRS_STRUCTURE:
            raise Exception("Unknown DRS structure %s" % drs_structure)
        return DRSFile.DRS_STRUCTURE[drs_structure]

    @staticmethod
    def from_dict(file_dict, drs_structure=BASELINE0):
        """:param file_dict: dictionary with the DRS components.
:type file_dict: dict
:param drs_structure: name of a DRS structure (key of :class:`DRSFile.DRS_STRUCTURE`)
:type drs_structure: str
:returns: (:class:`DRSFile`) generated from the given dictionary and DRS structure name"""
        return DRSFile(file_dict, drs_structure=drs_structure)

    @staticmethod
    def from_json(json_str, drs_structure=BASELINE0):
        """:param json_str: string with a json representation of the DRS components. Like the result from calling :class:`DRSFile.to_json`.
:type json_str: str
:param drs_structure: name of a DRS structure (key of :class:`DRSFile.DRS_STRUCTURE`)
:type drs_structure: str
:returns: (:class:`DRSFile`) generated from the given dictionary and DRS structure name"""
        return DRSFile.from_dict(json.loads(json_str), drs_structure=drs_structure)

    @staticmethod
    def search(drs_structure=BASELINE0, latest_version=True, path_only=False, **partial_dict):  # pragma nocover
        """DEPRECATED: Use solr_search instead!
        Simple search for files. It searches locally on the file system using :py:func:`glob.iglob`.
This means the values might contain jokers like '\*1960*'.

:param drs_structure: name of a DRS structure (key of :class:`DRSFile.DRS_STRUCTURE`)
:type drs_structure: str
:param latest_version: if this should be only the latest version available.
:type latest_version: bool
:param partial_dict: a dictionary with some DRS components representing the query.
:returns: Generator returning matching files"""
        log.warning("Deprecated: User solr_search instead")
        bl = DRSFile._getDrsStructure(drs_structure)
        search_dict = bl['defaults'].copy()
        search_dict.update(partial_dict)
        log.debug("Searching in %s using %s", drs_structure, search_dict)

        # only baseline 0 is versioned
        if latest_version and ('parts_versioned_dataset' not in bl):
            latest_version = False
            log.debug("No version information stored in the selected structure thus latest version is inactive.")

        local_path = bl['root_dir']
        for key in bl['parts_dir']:
            if key in search_dict:
                local_path = os.path.join(local_path, search_dict[key])
                del search_dict[key]    # remove it so we can see if all keys matched
            else:
                local_path = os.path.join(local_path, "*")

        # NOTE: We might have defaults for the datasets that are not appearing in the directories.
        if set(search_dict) - set(bl['defaults']):
            # ok, there are typos or non existing constraints in the search.
            # which are not in the defaults. Those are "strange" to the selected structure.
            mesg = "Unknown parameter(s) %s for %s." % (','.join(search_dict), drs_structure)
            similar_words = set()
            for w in search_dict:
                    similar_words.update(find_similar_words(w, bl['parts_dir']))
            if similar_words:
                mesg = "%s\n Did you mean this?\n\t%s" % (mesg, '\n\t'.join(similar_words))
            mesg = "%s\n\nFor %s try one of: %s" % (mesg, drs_structure, ','.join(bl['parts_dir']))

            raise Exception(mesg)

        # if the latest version is not required we may use a generator and yield a value as soon as it is found
        # If not we need to parse all until we can give the results out. We are not storing more than the latest
        # version, but if we could assure a certain order we return values as soon as we are done with a dataset
        datasets = {}
        for path in glob.iglob(local_path):

            blf = DRSFile.from_path(path, drs_structure)
            if not latest_version:
                if path_only:
                    yield path
                else:
                    yield blf
            else:
                # if not we need to check if the corresponding dataset version is recent
                ds = blf.to_dataset(versioned=False)
                if ds not in datasets or datasets[ds][0].get_version() < blf.get_version():
                    # if none or a newer version is found, re-init the dataset list
                    datasets[ds] = [blf]
                elif datasets[ds][0].get_version() == blf.get_version():
                    # if same version, add to previous (we are gathering multiple files per dataset)
                    datasets[ds].append(blf)

        if latest_version:
            # then return the results stored in datasets
            for latest_version_file in [v for sub in datasets.values() for v in sub]:
                if path_only:
                    latest_version_file.to_path()
                else:
                    yield latest_version_file

    @staticmethod
    def solr_search(drs_structure=None, latest_version=True, path_only=False, batch_size=10000, **partial_dict):
        """Search for files by relying on a Solr Index.*'.

:param drs_structure: name of a DRS structure (key of :class:`DRSFile.DRS_STRUCTURE`). This isn't mandatory anymore.
:type drs_structure: str
:param latest_version: if this should be only the latest version available.
:type latest_version: bool
:param path_only: If true returns a string with the path only, otherwise a complete DRSFile object.
:param batch_size: The size of the number of results that will be returned by each Solr call. 
:type batch_size: int
:param partial_dict: a dictionary with some DRS components representing the query. 
:returns: Generator returning matching files"""
        from evaluation_system.model.solr import SolrFindFiles
        if drs_structure is not None:
            partial_dict['data_type'] = drs_structure
        if path_only:
            for path in SolrFindFiles.search(batch_size=batch_size, **partial_dict):
                yield path
        else:
            for path in SolrFindFiles.search(batch_size=batch_size, **partial_dict):
                yield DRSFile.from_path(path)
