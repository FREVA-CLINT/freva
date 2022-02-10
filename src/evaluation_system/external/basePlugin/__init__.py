"""
This class represents the foundation of all University of Cologne plugins. 

@author: Robert Redl
rredl@meteo.uni-koeln.de 
"""

from evaluation_system.model.file import *
from evaluation_system.model.solr import SolrFindFiles
import time
from datetime import datetime
import os
from Logger import Logger
from ShellScriptHelper import ShellScript
from NCLhelper import NCLscript
import copy
import re
import netCDF4


def print_arguments(config_dict):
    Logger.Indent("-> started with parameters:", 4, 7)
    params = []
    for key, value in config_dict.items():
        params.append("-> %-15s = %s" % (key, value))
    params.sort()
    for param in params:
        Logger.Indent(param, 8, 29)


def apply_workarounds_for_path(filelist):
    """
    some decadal experiments are not located in the same location then other experiments that belong together.
    the result ist that
    the files are grouped together in unexpected ways. here the path are replaced by predefined aliases.
    """
    # check if all file have the same root
    roots = []
    for onefile in filelist:
        if not onefile.dict["root_dir"] in roots:
            roots.append(onefile.dict["root_dir"])
    has_multiple_roots = len(roots) > 1

    # check all files
    for i in range(len(filelist)):
        # some baseline0 model runs are located in a different folder
        # this only matters if the root of the files is not always the same
        if has_multiple_roots:
            match = re.match(
                "/miklip/integration/data4miklip/projectdata/baseline0/output1/MPI-M/MPI-ESM-LR/decadal(\d\d\d\d)/(day|mon|6hr)/atmos/"
                + filelist[i].dict["parts"]["variable"]
                + "/"
                + filelist[i].dict["parts"]["ensemble"],
                filelist[i].to_path(),
            )
            if match is not None:
                newfile = splittedFile([filelist[i]])
                replacement = (
                    "/miklip/integration/data4miklip/model/global/miklip/baseline0/output1/MPI-M/MPI-ESM-LR/decadal%s/%s/atmos/%s/%s/v20111122/%s"
                    % (
                        match.group(1),
                        match.group(2),
                        filelist[i].dict["parts"]["cmor_table"],
                        filelist[i].dict["parts"]["ensemble"],
                        filelist[i].dict["parts"]["variable"],
                    )
                )
                newpath = filelist[i].to_path().replace(match.group(0), replacement)
                newfile.set_fake_path(newpath)
                Logger.Indent(
                    "-> workaround: %s => %s" % (filelist[i].to_path(), newpath), 8, 11
                )
                filelist[i] = newfile


def get_time_format_and_start_and_end(name_or_file, allow_no_time=False):
    """
    extracts the time format and and parts dictionary entry from a DRSFile or from a file name
    """
    # is it a file object?
    if isinstance(name_or_file, splittedFile) or isinstance(name_or_file, DRSFile):
        timepart = name_or_file.dict["parts"]["time"]
        # is it a valid time part?
        if re.match("\d{6,12}-\d{6,12}", timepart) is None:
            timepart_match = re.search(
                "\d{6,12}-\d{6,12}", name_or_file.dict["parts"]["file_name"]
            )
            if timepart_match is not None:
                timepart = timepart_match.group(0)
                # repair time part in dictionary
                name_or_file.dict["parts"]["time"] = timepart
            else:
                if not allow_no_time:
                    Logger.Error(
                        "Unable to extract time of file %s" % dfile.to_path(), -1
                    )
                else:
                    timepart = None
    # it is not a file object, that means it is a string containing a file name
    else:
        timepart_match = re.search("\d{6,12}-\d{6,12}", name_or_file)
        if timepart_match != None:
            timepart = timepart_match.group(0)
        else:
            if not allow_no_time:
                Logger.Error("Unable to extract time from string '%s'" % timestr, -1)
            else:
                timepart = None

    # check if we have a time part
    if timepart is None:
        return None, None, None
    else:
        # find the format of the date time string
        if len(timepart) == 17:
            datefmt = "%Y%m%d"
        elif len(timepart) == 21:
            datefmt = "%Y%m%d%H"
        elif len(timepart) == 23:
            datefmt = "%Y%m%d%H%M"
        elif len(timepart) == 13:
            datefmt = "%Y%m"
        else:
            Logger.Error("unable to get time_frequency from file '%s'" % name_or_file)
            Logger.Error(
                "only the time_frequencies 'day', '6hr', and 'mon' are so far supported!",
                -1,
            )
        # split and convert
        timepart_split = timepart.split("-")
        try:
            starttime = datetime.strptime(timepart_split[0], datefmt)
            endtime = datetime.strptime(timepart_split[1], datefmt)
        except ValueError as ve:
            Logger.Error(
                "The filename %s contains an invalid date: %s"
                % (dfile.to_path(), ve.message),
                -1,
            )
        return (datefmt, starttime, endtime)


def get_start_and_end_time_from_DRSFile(dfile, include_str=True, only_str=False):
    """
    returns a tuple (start,end,startstr,endstr)
    start,end       = date objects (only_str=False)
    startstr,endstr = string parts of the file name (only with include_str=True)
    """
    timepart = dfile.dict["parts"]["time"]
    # workaround for TRMM:
    if re.match("\d{6,12}-\d{6,12}", timepart) is None:
        timepart_match = re.search(
            "\d{6,12}-\d{6,12}", dfile.dict["parts"]["file_name"]
        )
        if timepart_match is not None:
            timepart = timepart_match.group(0)
            dfile.dict["parts"]["time"] = timepart
        else:
            Logger.Error("Unable to extract time of file %s" % dfile.to_path(), -1)
    # find the format of the date time string
    if len(timepart) == 17:
        datefmt = "%Y%m%d"
    elif len(timepart) == 21:
        datefmt = "%Y%m%d%H"
    elif len(timepart) == 25:
        datefmt = "%Y%m%d%H%M"
    elif len(timepart) == 13:
        datefmt = "%Y%m"
    else:
        Logger.Error("unable to get time_frequency from file '%s'" % dfile)
        Logger.Error(
            "only the time_frequencies 'day', '6hr', and 'mon' are so far supported!",
            -1,
        )
    # split and convert
    timepart_split = timepart.split("-")
    try:
        starttime = datetime.strptime(timepart_split[0], datefmt)
        endtime = datetime.strptime(timepart_split[1], datefmt)
    except ValueError as ve:
        Logger.Error(
            "The filename %s contains an invalid date: %s"
            % (dfile.to_path(), ve.message),
            -1,
        )
    if include_str and not only_str:
        return (starttime, endtime, timepart_split[0], timepart_split[1])
    elif include_str == True and only_str == True:
        return timepart_split[0], timepart_split[1]
    else:
        return starttime, endtime


def get_start_and_end_time_from_string(timestr, allow_no_time=False):
    timepart_match = re.search("\d{6,12}-\d{6,12}", timestr)
    if timepart_match is not None:
        timepart = timepart_match.group(0)
    else:
        if allow_no_time:
            return None, None
        else:
            Logger.Error("Unable to extract time from string '%s'" % timestr, -1)
    # find the format of the date time string
    if len(timepart) == 17:
        datefmt = "%Y%m%d"
    elif len(timepart) == 21:
        datefmt = "%Y%m%d%H"
    elif len(timepart) == 25:
        datefmt = "%Y%m%d%H%M"
    elif len(timepart) == 13:
        datefmt = "%Y%m"
    else:
        if allow_no_time:
            return None, None
        else:
            Logger.Error("unable to get time_frequency from time string '%s'" % timestr)
            Logger.Error(
                "only the time_frequencies 'day', '6hr', and 'mon' are so far supoorted!",
                -1,
            )
    # split and convert
    timepart_split = timepart.split("-")

    try:
        starttime = datetime.strptime(timepart_split[0], datefmt)
        endtime = datetime.strptime(timepart_split[1], datefmt)
    except ValueError as ve:
        if allow_no_time:
            return None, None
        else:
            Logger.Error(
                "The string '%s' contains an invalid date: %s" % (timestr, ve.message),
                -1,
            )
    return starttime, endtime


def solr_search_multivar(variables, ssargs):
    """
    use solr_search to find files for multiple variables
    """
    allfiles = []
    for variable in variables:
        ssargs["variable"] = variable
        allfiles.extend(DRSFile.solr_search(**ssargs))
    del ssargs["variable"]
    result = []
    for onefile in allfiles:
        if (
            os.path.exists(onefile.to_path())
            and not onefile.to_path().endswith(".nc.save")
            and not os.path.getsize(onefile.to_path()) == 0
        ):
            result.append(onefile)
        else:
            Logger.Warning(
                "the file '%s' does not exist, is empty, or ends with '.nc.save'!"
                % onefile.to_path()
            )
    return result


def number_of_files_in_folder(folder):
    """
    checks the presents of a folder and counts the number of files it contains.
    returns number of files found or -1 if the folder is not present.
    """
    if not os.path.exists(folder):
        return -1
    nfiles = 0
    for root, dirs, files in os.walk(folder):
        nfiles += len(files)
    return nfiles


class splittedFile(object):
    """
    Files of the same experiment are sometimes splitted up if they would become to large otherwise. These
    splitted files
    are can by grouped together in this class and treated as one.
    """

    def __init__(self, filelist, lead_year=None):
        """
        create a new splittedFile object from a list of DRSFile objects
        """
        self.parts = copy.deepcopy(filelist)
        self.dict = copy.deepcopy(filelist[0].dict)

        # get the first start time and the last end time
        first = None
        last = None
        for onefile in self.parts:
            # get the current start and end time of this file
            datefmt, start, end = get_time_format_and_start_and_end(onefile)
            if lead_year is not None:
                # calculate the new start and end time
                start = datetime(
                    year=start.year + lead_year - 1,
                    month=start.month,
                    day=start.day,
                    hour=start.hour,
                )
                end = datetime(
                    year=start.year, month=end.month, day=end.day, hour=end.hour
                )
            if first is None or start < first:
                first = start
            if last is None or end > last:
                last = end

        firsty = first.year
        lasty = last.year
        first = datetime(1900, first.month, first.day, first.hour, first.minute)
        last = datetime(1900, last.month, last.day, last.hour, last.minute)
        self.dict["parts"]["time"] = "%s%s-%s%s" % (
            str(firsty),
            first.strftime(datefmt)[4:],
            str(lasty),
            last.strftime(datefmt)[4:],
        )
        # merge variables
        # create at first a list of all variables
        variables = []
        for onefile in self.parts:
            if onefile.dict["parts"]["variable"] not in variables:
                variables.append(onefile.dict["parts"]["variable"])
        if len(variables) > 1:
            self.dict["parts"]["variable"] = "_".join(variables)
        # allow the path to be overridden
        self.manual_set_path = None

    def __str__(self):
        """
        get a string representation
        """
        return self.to_path(fake=False, separator="\n")

    def has_multiple_parts(self):
        return len(self.parts) > 1

    def to_path(self, fake=False, as_list=False, separator=" "):
        """
        returns a space separated string with all paths if fake == False,
        otherwise a path is generated which would fit to a single file with the same content
        """

        def get_path_string(x, pfake=False):
            if isinstance(x, splittedFile):
                return x.to_path(fake=pfake, separator="\n")
            else:
                return x.to_path()

        if fake:
            if self.manual_set_path is not None:
                return self.manual_set_path
            # get the first start time and the last end time
            return (
                get_path_string(self.parts[0], pfake=True)
                .replace(
                    self.parts[0].dict["parts"]["time"], self.dict["parts"]["time"]
                )
                .replace(
                    self.parts[0].dict["parts"]["variable"],
                    self.dict["parts"]["variable"],
                )
            )
        else:
            if as_list:
                result = []
                for onefile in self.parts:
                    if not isinstance(onefile, splittedFile):
                        result.append(onefile.to_path())
                    else:
                        result.extend(onefile.to_path(fake=False, as_list=True))
                return result
            else:
                return separator.join(map(lambda x: get_path_string(x), self.parts))

    def set_fake_path(self, new_path):
        """
        override the real path with a fake
        """
        self.manual_set_path = new_path

    @classmethod
    def get_fake_path(cls, onefile):
        """
        if the argument is an instance of splittedFile, then the fake path is returned. Otherwise the real path.
        """
        if isinstance(onefile, splittedFile):
            return onefile.to_path(fake=True)
        else:
            return onefile.to_path()


class basePlugin(object):
    def __init__(
        self, output=None, project="baseline1", model="mpi-esm-lr", experiment=None
    ):
        # store some information for later usage
        if output is None:
            raise Exception("No output directory specified!")
        subdir = "%s_%s_%s" % (time.strftime("%Y%m%d-%H%M%S"), project, model)
        subdir = subdir.replace("_*", "")
        if experiment is not None and experiment != "*":
            subdir += "_%s" % experiment.replace("*", "")
        # use the subdirectory only if the output and plotdir are the default dirs
        self.outputfiles = []
        self.outputfiles_ensstat = []

    def search_files(
        self,
        decadals=None,
        project="baseline1",
        firstyear=None,
        lastyear=None,
        product="*",
        time_frequency="6hr",
        model="mpi-esm-lr",
        ensembles=["*"],
        experiment=None,
        variable="ta",
        institute="MPI-M",
        realm="atmos",
        driving_model=None,
        rcm_ensemble=None,
        domain=None,
        find_variables=False,
    ):
        """
        use solr_search to find the files needed by the plugin
        set find_variables=True to get a list of available variables instead of searching files
        """
        # convert some arguments

        #         if '*' in ensembles:
        #             Logger.Error('All ensembles not allowed\n'
        #                          'Please select one',-1)

        if ensembles != "\*":
            ensembles = ensembles.split(",")
        else:
            ensembles = [ensembles]
        if decadals is not None:
            years = list(map(int, decadals))
        else:
            years = None
        if firstyear is not None:
            firstyear = int(firstyear)
        if lastyear is not None:
            lastyear = int(lastyear)

        # use solr_search to get the input files --------------------------------------------------
        # construct a search string for experiments
        experiment_prefix = experiment
        if experiment_prefix is None or experiment_prefix == "*":
            if project.lower() == "baseline0":
                experiment_prefix = "decadal"
            elif project.lower() == "baseline1":
                experiment_prefix = "decs4e"
            elif project.lower() == "prototype":
                experiment_prefix = "dffs4e"
            elif project.lower() == "cmip5":
                experiment_prefix = "decadal"
            elif project.lower() == "historical":
                experiment_prefix = "historical"
            else:
                experiment_prefix = "*"
        # if not experiment_prefix.endswith("*"):
        #    experiment_prefix += "*"

        # compose solr_search arguments
        ssargs = {}
        ssargs["project"] = project
        ssargs["institute"] = institute
        ssargs["realm"] = realm
        if type(variable) == list:
            variables = variable
        else:
            variables = [variable]
        ssargs["time_frequency"] = time_frequency
        # are there products in this project?
        product_facets = SolrFindFiles.facets(facets=["product"], **ssargs)
        if len(product_facets["product"]) > 0:
            ssargs["product"] = product
        # are there models in this project?
        model_facets = SolrFindFiles.facets(facets=["model"], **ssargs)
        if len(model_facets["model"]) > 0:
            ssargs["model"] = model
        # are there multiple experiments?
        experiment_facets = SolrFindFiles.facets(facets=["experiment"], **ssargs)
        if len(experiment_facets["experiment"]) > 0:
            ssargs["experiment"] = experiment_prefix
        # additional parameters for regional models
        if rcm_ensemble is not None:
            rcm_ensemble_facets = SolrFindFiles.facets(
                facets=["rcm_ensemble"], **ssargs
            )
            if len(rcm_ensemble_facets["rcm_ensemble"]) > 0:
                ssargs["rcm_ensemble"] = rcm_ensemble
        if driving_model is not None:
            driving_model_facets = SolrFindFiles.facets(
                facets=["driving_model"], **ssargs
            )
            if len(driving_model_facets["driving_model"]) > 0:
                ssargs["driving_model"] = driving_model
        if domain is not None:
            domain_facets = SolrFindFiles.facets(facets=["domain"], **ssargs)
            if len(domain_facets["domain"]) > 0:
                ssargs["domain"] = domain

        # search variables instead of files?
        if find_variables:
            variable_facets = SolrFindFiles.facets(facets=["variable"], **ssargs)
            return variable_facets["variable"]

        # put all files into a list

        self.inputfiles = []
        if years is not None or firstyear is not None or lastyear is not None:
            self.inputfilesByDecade = {}
            # we have multiple experiments that contain the decade
            if (
                "experiment" in ssargs
                and project != "observations"
                and project != "reanalysis"
                and years is not None
            ):
                for year in years:
                    yearfiles = []
                    ssargs["experiment"] = "%s%d" % (experiment_prefix, year)
                    for ens in ensembles:
                        if ens != "*":
                            ssargs["ensemble"] = ens
                        for onefile in solr_search_multivar(variables, ssargs):
                            self.inputfiles.append(onefile)
                            yearfiles.append(onefile)
                    self.inputfilesByDecade[year] = yearfiles

            # we have only one experiment. fetch all files and filter them by year
            elif firstyear is not None or lastyear is not None:
                for ens in ensembles:
                    if ens != "*":
                        ssargs["ensemble"] = ens
                    for onefile in solr_search_multivar(variables, ssargs):
                        starttime, endtime = get_start_and_end_time_from_DRSFile(
                            onefile, include_str=False
                        )
                        if firstyear is None and any(
                            [
                                True
                                for e in range(starttime.year, endtime.year + 1, 1)
                                if e <= lastyear
                            ]
                        ):
                            self.inputfiles.append(onefile)
                        elif lastyear is None and any(
                            [
                                True
                                for e in range(starttime.year, endtime.year + 1, 1)
                                if e >= firstyear
                            ]
                        ):
                            self.inputfiles.append(onefile)
                        elif any(
                            [
                                True
                                for e in range(firstyear, lastyear + 1, 1)
                                if e in range(starttime.year, endtime.year + 1, 1)
                            ]
                        ):
                            self.inputfiles.append(onefile)

            else:
                for ens in ensembles:
                    if ens != "*":
                        ssargs["ensemble"] = ens
                    for onefile in solr_search_multivar(variables, ssargs):
                        starttime, endtime = get_start_and_end_time_from_DRSFile(
                            onefile, include_str=False
                        )
                        for year in years:
                            if starttime.year > year and endtime.year <= year + 10:
                                self.inputfiles.append(onefile)
                                if year not in self.inputfilesByDecade:
                                    self.inputfilesByDecade[year] = [onefile]
                                else:
                                    self.inputfilesByDecade[year].append(onefile)
                                break
                                # we want all files, not only those for a special decade
        else:
            self.inputfilesByDecade = None
            for ens in ensembles:
                if ens != "*":
                    ssargs["ensemble"] = ens
                for onefile in solr_search_multivar(variables, ssargs):
                    self.inputfiles.append(onefile)

        # nothing found? cancel!
        if len(self.inputfiles) == 0:
            Logger.Error(
                "No input files found!\n"
                "Data-Browser command:\t"
                "freva --databrowser project='%s' product='%s' institute='%s' model='%s' experiment='%s'"
                " time_frequency='%s' realm='%s' variable='%s'"
                % (
                    project,
                    product,
                    institute,
                    model,
                    experiment,
                    time_frequency,
                    realm,
                    variable,
                ),
                -1,
            )

        # changed the time part if only a single lead year is of interest or remove files that do not belong to the
        # requested lead year

        # check for overlapping time-periods within the same folder
        self.inputfiles = self.remove_overlapping_time_periods_from_file_list(
            self.inputfiles
        )

        # check if all ensemble members have the same number of files
        self.inputfiles = self.check_ensemble_completeness(self.inputfiles)

        # repair some known special cases
        apply_workarounds_for_path(self.inputfiles)

        # merge multiple variables
        merged_by_var = self.merge_multiple_variables(self.inputfiles)
        if len(merged_by_var) == 0:
            Logger.Error("no files found for different variables and same time steps!")

            # group splitted files
            # self.inputfiles_merged = self.split_file_list_by_timecontinously(merged_by_var, return_splittedFile=True)

            # store information about the ensemble members to which the inputfiles belong
            # self.rcm_ensemble_members = Set()
            # for onfile in self.inputfiles:
            #    if "rcm_ensemble" in onfile.dict["parts"] and not onefile.dict["parts"]["rcm_ensemble"] in self.rcm_ensemble_members:
            #        self.rcm_ensemble_members.add(onefile.dict["parts"]["rcm_ensemble"])

    def group_input_by(self, files, groupby="ensemble", groupby2=None):
        """
        group files that belong to the same dataset and only differ by the ensemble member together.
        @param  files   list of DRSFile objects
        @returns        list of lists that contain ensemble groups, None if no group was found
        """

        def get_dataset_without_groupby(dfile):
            if isinstance(dfile, splittedFile):
                ds = os.path.basename(dfile.to_path(fake=True))
            else:
                ds = os.path.basename(dfile.to_path())
            dsens = dfile.dict["parts"][groupby]
            if groupby2 is not None and groupby2 in dfile.dict["parts"]:
                dsens2 = dfile.dict["parts"][groupby2]
                ds = ds.replace(dsens2, "<%s>" % groupby2)
            if groupby == "experiment":
                return dsens
            else:
                return ds.replace(dsens, "<%s>" % groupby)

        # check if it is possible to group the files by the given argument
        if groupby not in files[0].dict["parts"]:
            return None

        # put all file in a dictionary where the key is the dataset.
        # file that belong to the same dataset are placed in lists
        datasets = {}
        for onefile in files:
            dsname = get_dataset_without_groupby(onefile)
            if dsname in datasets:
                datasets[dsname].append(onefile)
            else:
                datasets[dsname] = [onefile]

        # remove groups that only contain one file
        keys_to_remove = []
        for key, value in datasets.items():
            if len(value) < 2:
                keys_to_remove.append(key)
        if len(keys_to_remove) > 0:
            for key in keys_to_remove:
                del datasets[key]

        # check time ranges for experiments
        keys_to_remove = []
        new_datasets = {}
        if groupby == "experiment":
            for key, value in datasets.items():
                newlist = self.split_file_list_by_timecontinously(value)
                if newlist is not None:
                    keys_to_remove.append(key)
                    for i in range(0, len(newlist)):
                        new_datasets["%s_%d" % (key, i)] = newlist[i]
            if len(keys_to_remove) > 0:
                for key in keys_to_remove:
                    del datasets[key]
                for key, value in new_datasets.items():
                    datasets[key] = value
            # remove again groups that only contain one file
            keys_to_remove = []
            for key, value in datasets.items():
                if len(value) < 2:
                    keys_to_remove.append(key)
            if len(keys_to_remove) > 0:
                for key in keys_to_remove:
                    del datasets[key]

        if len(datasets) > 0:
            return datasets
        else:
            return None

    def check_ensemble_completeness(self, files):
        """
        count the files for all ensemble member. remove members that have less members then others
        """
        # do nothing if we don't have an ensemble
        if "ensemble" not in files[0].dict["parts"]:
            return files
        # first step: group all files by their ensemble membership
        ensembles = {}
        for onefile in files:
            ensemble_part = onefile.dict["parts"]["ensemble"]
            if "rcm_ensemble" in onefile.dict["parts"]:
                ensemble_part += "-" + onefile.dict["parts"]["rcm_ensemble"]
            if ensemble_part not in ensembles:
                ensembles[ensemble_part] = [onefile]
            else:
                ensembles[ensemble_part].append(onefile)
        # find the maximum number of files per member
        max_files = 0
        for ensemble_part, filelist in ensembles.items():
            if len(filelist) > max_files:
                max_files = len(filelist)
        # copy all ensemble members with the maximal number of files to the result list
        result = []
        for ensemble_part, filelist in ensembles.items():
            if len(filelist) == max_files:
                result.extend(filelist)
            else:
                Logger.Indent(
                    "-> removed ensemble member %s, not enough files found!"
                    % ensemble_part,
                    8,
                    11,
                )
        # sort the result list
        return sorted(result, key=splittedFile.get_fake_path)

    def remove_overlapping_time_periods_from_file_list(self, filelist):
        """
        this is a workaround only. Removed are files that are located in the same folder but have overlapping
        time periods
        """
        # the list has to be sorted
        files = sorted(filelist, key=lambda x: x.to_path())
        # a dictionary for the periods, the folder is the key
        periods_per_folder = {}
        result = []
        for onefile in files:
            start, end = get_start_and_end_time_from_DRSFile(onefile, include_str=False)
            folder = os.path.dirname(onefile.to_path())
            if folder in periods_per_folder:
                old_period = periods_per_folder[folder]
                if old_period[0] <= start and old_period[1] >= start:
                    Logger.Warning(
                        "found overlapping time periods in folder '%s'" % folder
                    )
                    Logger.Warning("removing file '%s' from list" % onefile.to_path())
                else:
                    new_period = (old_period[0], end)
                    periods_per_folder[folder] = new_period
                    result.append(onefile)
            else:
                periods_per_folder[folder] = (start, end)
                result.append(onefile)
        return result

    def merge_multiple_variables(self, files):
        """
        creates a list of splitted files if more than one variable is included in the list of files.
        otherwise the list is returned unchanged.
        """
        # count the different variables
        variables = []
        for onefile in files:
            if onefile.dict["parts"]["variable"] not in variables:
                variables.append(onefile.dict["parts"]["variable"])
        variables.sort()
        # separate the files by variable
        files_by_var = []
        all_times = []
        all_ensemble = []
        for var in variables:
            file_list = {}
            for onefile in files:
                if onefile.dict["parts"]["variable"] == var:
                    time_part = onefile.dict["parts"]["time"]
                    ensemble_part = ""
                    if "ensemble" in onefile.dict["parts"]:
                        ensemble_part = onefile.dict["parts"]["ensemble"]
                    if "rcm_ensemble" in onefile.dict["parts"]:
                        ensemble_part += "-" + onefile.dict["parts"]["rcm_ensemble"]
                    file_list[time_part + ensemble_part] = onefile
                    if time_part not in all_times:
                        all_times.append(time_part)
                    if ensemble_part not in all_ensemble:
                        all_ensemble.append(ensemble_part)
            files_by_var.append(file_list)
        # create merged files from all time steps
        new_files = []
        for time_part in all_times:
            for ensemble_part in all_ensemble:
                file_list = []
                for ivar in range(len(variables)):
                    key = time_part + ensemble_part
                    if key in files_by_var[ivar]:
                        file_list.append(files_by_var[ivar][key])
                if len(file_list) == len(variables):
                    if len(file_list) == 1:
                        new_files.append(file_list[0])
                    else:
                        new_files.append(splittedFile(file_list))
                else:
                    Logger.Indent(
                        "-> %s not available for all variables in %s"
                        % (time_part, ensemble_part),
                        8,
                        11,
                    )
                    for onefile in file_list:
                        Logger.Indent("-> found only: %s" % onefile.to_path(), 12, 27)
        return sorted(new_files, key=splittedFile.get_fake_path)

    def split_file_list_by_timecontinously(self, files, return_splittedFile=False):
        """
        splits a list of files into a list of lists in case of time gaps
        @returns newlist or None if nothing was splitted.
        """

        def get_sort_key(onefile):
            """
            create a key for sorting the files depending on whether we have a selected lead_year or not
            """
            if self.lead_year is None:
                return onefile.to_path()
            else:
                key = ""
                if "ensemble" in onefile.dict["parts"]:
                    key += onefile.dict["parts"]["ensemble"]
                if "rcm_ensemble" in onefile.dict["parts"]:
                    key += onefile.dict["parts"]["rcm_ensemble"]
                key += os.path.basename(onefile.to_path())
                return key

        def get_dir_without_experiment(onefile):
            """
            if we use the lead_year, then files that belong together are not located in the same folder.
            remove the experiment in this case
            """
            if isinstance(onefile, splittedFile):
                pathstr = onefile.to_path(fake=True)
            else:
                pathstr = onefile.to_path()
            if self.lead_year is None:
                return os.path.dirname(pathstr)
            else:
                return os.path.dirname(pathstr).replace(
                    onefile.dict["parts"]["experiment"], ""
                )

        # sort the files in the way they likely extend each other
        sortedfiles = sorted(files, key=lambda x: get_sort_key(x))
        newlist = []
        newpart = []
        laststart = None
        lastend = None
        lastdir = get_dir_without_experiment(files[0])
        time_frequency = files[0].dict["parts"]["time_frequency"]
        # a gap of two days is allowed, because some models work with 30 day month
        if time_frequency == "day":
            max_delta_days = 2
        elif time_frequency == "6hr":
            max_delta_days = 2
        elif time_frequency == "mon":
            max_delta_days = 31
        else:
            Logger.Error(
                "unable to get time_frequency from file '%s'" % files[0].to_path()
            )
            Logger.Error(
                "only the time_frequencies 'day', '6hr', and 'mon' are so far supported!",
                -1,
            )
        for onefile in sortedfiles:
            starttime, endtime = get_start_and_end_time_from_DRSFile(
                onefile, include_str=False
            )
            currentdir = get_dir_without_experiment(onefile)
            if len(newpart) == 0:
                newpart.append(onefile)
            else:
                delta = starttime - lastend
                if (
                    delta.days > max_delta_days
                    or delta.days < 0
                    or currentdir != lastdir
                ):
                    newlist.append(newpart)
                    newpart = [onefile]
                else:
                    newpart.append(onefile)
            laststart = starttime
            lastend = endtime
            lastdir = currentdir
        if len(newpart) > 0:
            newlist.append(newpart)
        if len(newlist) > 0:
            if not return_splittedFile:
                return newlist
            else:
                # create splittedFile objects from the list
                sflist = list(map(lambda x: splittedFile(x), newlist))
                return sflist
        else:
            return None

    def change_time_part_to_lead_year(self, filelist, lead_year):
        """
        create splittedFile instances of the files given in filelist with a reduced time part in the file name
        """
        if lead_year > 10 or lead_year < 1:
            Logger.Error("Only lead years between 1 and 10 are allowed!", -1)
        newlist = []
        for onefile in filelist:
            start, end = get_start_and_end_time_from_DRSFile(onefile, include_str=False)
            if end.year - start.year + 1 < lead_year:
                Logger.Warning(
                    "file to short for lead year %d: %s"
                    % (lead_year, onefile.to_path())
                )
            else:
                newlist.append(splittedFile([onefile], lead_year=lead_year))
        return newlist

    def filter_inputfiles_by_lead_year(self, filelist, lead_year):
        """
        files those are created by split_file_list_by_time-continously and those contain single files only one year long
        are the input to this function. returned is a list of DSRfile objects that have the correct lead year
        """
        result = []
        for onefile in filelist:
            # find start and end for the merged file
            start, end = get_start_and_end_time_from_DRSFile(onefile, include_str=False)
            lead_start = datetime(start.year + lead_year - 1, 1, 1, 0, 0, 0)
            lead_end = datetime(start.year + lead_year - 1, 12, 31, 23, 59, 59)
            # now loop over all parts of this file to find the ones that belong to the correct lead year
            for onepart in onefile.parts:
                fstart, fend = get_start_and_end_time_from_DRSFile(
                    onepart, include_str=False
                )
                if fstart >= lead_start and fend <= lead_end:
                    result.append(onepart)
        return result

    def get_output_from_input_name(self, name, files=None):
        """
        construct the name of an output file from an input file
        """
        if name is not None and files is None:
            output_name = self.output + "/" + os.path.basename(name)
        if name is None and files is not None:
            # find first and last date to construct a new file name
            first = None
            last = None
            for onefile in files:
                (
                    starttime,
                    endtime,
                    startstr,
                    endstr,
                ) = get_start_and_end_time_from_DRSFile(onefile)
                if first is None:
                    first = starttime
                if last is None:
                    last = endtime
                if starttime < first:
                    first = starttime
                if endtime > last:
                    last = endtime
            newname = (
                files[0]
                .to_path()
                .replace(files[0].dict["parts"]["time"], "%s-%s" % (startstr, endstr))
            )
            return self.get_output_from_input_name(newname)
        return output_name

    def run_list_of_commands(self, commands, dryrun):
        # run the commands
        if dryrun:
            Logger.Info("\nDryrun! Not executed commands: ", color="red")
            for cmd in commands:
                if cmd.workpath is None:
                    print(cmd.getCommand() + "\n")
                else:
                    print("cd %s ; %s\n" % (cmd.workpath, cmd.getCommand()))
        else:
            SLURM_NTASKS_PER_NODE = os.getenv("SLURM_NTASKS_PER_NODE")
            if SLURM_NTASKS_PER_NODE is not None:
                SLURM_NTASKS_PER_NODE = int(SLURM_NTASKS_PER_NODE)
                Logger.Info(
                    "Number of processes limited by SLURM to %d" % SLURM_NTASKS_PER_NODE
                )
            exitcodes = ShellScript.run_scripts_parallel(
                commands, nproc=SLURM_NTASKS_PER_NODE
            )
            # check for any errors
            for c in exitcodes:
                if c[0] != 0:
                    raise Exception(
                        "exitcode: %d during parallel execution:\ncommand:\n%s\n\noutput:\n%s!"
                        % (c[0], c[2], c[1])
                    )

    def calculate_ensemble_stat(
        self, plugin_path, dryrun=False, separate=True, has_mon=False
    ):
        """
        calculate ensemble mean, min, max, etc.
        @separate   set to True if you don't want to add the files to the list of output files. The additional list
        outputfiles_ensstat only will be filled.
        """
        if self.ensemble_groups is None:
            Logger.Error("no ensemble groups!", -1)

        stats = ["ensmean", "ensmin", "ensmax"]

        # iterate over all groups and use cdo to calculate the statistics with CDO
        commands = []
        for key, value in self.ensemble_groups.items():
            group_files = []
            for stat in stats:
                output_name = self.get_output_from_input_name(
                    key.replace("<ensemble>", stat).replace("<rcm_ensemble>", stat)
                )
                group_files.append(output_name)
                if not separate:
                    self.outputfiles.append(output_name)
                command = ShellScript("cdo", check=False)
                command.addFlag("-O")
                command.addPositionalArgument(stat)
                for ifile in value:
                    if isinstance(ifile, splittedFile):
                        command.addPositionalArgument(
                            self.get_output_from_input_name(ifile.to_path(fake=True))
                        )
                    else:
                        command.addPositionalArgument(
                            self.get_output_from_input_name(ifile.to_path())
                        )
                command.addPositionalArgument(output_name)
                commands.append(command)
                # is there an additional output with the same names but a different extension
                if has_mon:
                    output_name2 = output_name.replace(".nc", "_mon.nc")
                    if not separate:
                        self.outputfiles.append(output_name2)
                    group_files.append(output_name2)
                    command2 = ShellScript("cdo", check=False)
                    command2.addPositionalArgument(stat)
                    for ifile in value:
                        if isinstance(ifile, splittedFile):
                            command2.addPositionalArgument(
                                self.get_output_from_input_name(
                                    ifile.to_path(fake=True)
                                ).replace(".nc", "_mon.nc")
                            )
                        else:
                            command2.addPositionalArgument(
                                self.get_output_from_input_name(
                                    ifile.to_path()
                                ).replace(".nc", "_mon.nc")
                            )
                    command2.addPositionalArgument(output_name2)
                    commands.append(command2)
            self.outputfiles_ensstat.append(group_files)

        # run the commands
        self.run_list_of_commands(commands, dryrun)

    def get_variable_unit(self, varname, filename):
        """
        open the netcdf file and read the unit attribute of the given variable (if available)
        """
        # check existence and open nc file
        if not os.path.exists(filename):
            Logger.Error("file not found: '%s' (get_variable_unit)" % filename, -1)
        nc = netCDF4.Dataset(filename, "r")

        # get the requested variable
        if varname not in nc.variables:
            Logger.Error(
                "variable '%s' not found in file '%s' (get_variable_unit)"
                % (varname, filename)
            )
        var = nc.variables[varname]
        units = var.units

        # close nc file
        nc.close()
        return units
