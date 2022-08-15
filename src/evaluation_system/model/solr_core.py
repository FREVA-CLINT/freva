"""
Created on 11.03.2013

@author: Sebastian Illing / estani

This package encapsulate access to a solr instance (not for search but for administration)
We define two cores::

* files: all files  - id is file (full file path)
* latest: only those files from the latest dataset version - id is file_no_version (full file path *wothout* version information)

"""
from __future__ import annotations
import os
import shutil
import urllib
import urllib.request
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

from evaluation_system.model.file import DRSFile
from evaluation_system.misc import config, logger as log
from evaluation_system.misc.utils import get_solr_time_range
from evaluation_system.misc.exceptions import CommandError


class SolrCore:
    """Encapsulate access to a Solr instance"""

    def __init__(
        self,
        core=None,
        host=None,
        port=None,
        instance_dir=None,
        data_dir=None,
        get_status=True,
    ):
        """Create the connection pointing to the proper solr url and core.

        :param core: The name of the core referred (default: loaded from config file)
        :param host: the hostname of the Solr server (default: loaded from config file)
        :param port: The port number of the Solr Server (default: loaded from config file)
        :param instance_dir: the core instance directory (if empty but the core exists it will get downloaded from Solr)
        :param data_dir: the directory where the data is being kept (if empty but the core exists it will
        get downloaded from Solr)"""

        self.host = host or config.get(config.SOLR_HOST)
        self.port = port or config.get(config.SOLR_PORT)
        self.core = core or config.get(config.SOLR_CORE)
        self.solr_url = f"http://{self.host}:{self.port}/solr/"
        self.core_url = self.solr_url + self.core + "/"
        self.instance_dir = instance_dir
        self.data_dir = data_dir

        if get_status:
            st = self.status()
        else:
            st = {}
        if self.instance_dir is None and "instanceDir" in st:
            self.instance_dir = st["instanceDir"]
        if self.data_dir is None and "dataDir" in st:
            self.data_dir = st["dataDir"]
        else:
            self.data_dir = "data"

        # Other Defaults
        import socket

        socket.setdefaulttimeout(20)

    def __str__(self):
        return "<SolrCore %s>" % self.core_url

    def post(self, list_of_dicts, auto_list=True, commit=True):
        """Sends some json to Solr for ingestion.

        :param list_of_dicts: either a json or more normally a list of json instances that will be sent to Solr for ingestion
        :param auto_list: avoid packing list_of dicts in a directory if it's not one
        :param commit: send also a Solr commit so that changes can be seen immediately."""
        if auto_list and not isinstance(list_of_dicts, list):
            list_of_dicts = [list_of_dicts]
        endpoint = "update/json?"
        if commit:
            endpoint += "commit=true"
        query = self.core_url + endpoint
        log.debug(query)
        post_data = json.dumps(list_of_dicts).encode("ascii")
        req = urllib.request.Request(query, post_data)
        req.add_header("Content-type", "application/json")

        return urllib.request.urlopen(req).read()

    def get_json(self, endpoint, use_core=True, check_response=True):
        """Return some json from server. Is the raw access to Solr.

        :param endpoint: The endpoint, path missing after the core url and all parameters encoded in it (e.g. 'select?q=*')
        :param use_core: if the core info is used for generating the endpoint. (if False, then == self.core + '/' + endpoint)
        :param check_response: If the response should be checked for errors. If True, raise an exception if something is
         wrong (default: True)"""
        if "?" in endpoint:
            endpoint += "&wt=json"
        else:
            endpoint += "?wt=json"

        if use_core:
            query = self.core_url + endpoint
        else:
            query = self.solr_url + endpoint
        log.debug(query)
        try:
            req = urllib.request.Request(query)
            response = json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as error:
            raise ValueError("Bad databrowser request") from error
        if response["responseHeader"]["status"] != 0:
            raise ValueError(
                "Error while accessing Core %s. Response: %s" % (self.core, response)
            ) from error

        return response

    def get_solr_fields(self):
        """Return information about the Solr fields. This is dynamically generated and because of
        dynamicFiled entries in the Schema, this information cannot be inferred from anywhere else."""
        answer = self.get_json("admin/luke")["fields"]
        # TODO: Solr has a language facet. Until we know why, delete it
        if isinstance(answer, dict):
            try:
                del answer["language"]
            except KeyError:
                pass
        else:
            try:
                answer.remove("language")
            except ValueError:
                pass
        return answer

    def create(
        self,
        instance_dir=None,
        data_dir=None,
        config="solrconfig.xml",
        schema="schema.xml",
        check_if_exist=True,
    ):
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
            raise FileNotFoundError(
                "Expected Solr Core configuration not found in %s" % self.instance_dir
            )

        if data_dir is not None:
            self.data_dir = data_dir

        return self.get_json(
            "admin/cores?action=CREATE&name=%s" % self.core
            + "&instanceDir=%s" % self.instance_dir
            + "&config=%s" % config
            + "&schema=%s" % schema
            + "&dataDir=%s" % self.data_dir,
            use_core=False,
        )

    def reload(self):
        """Reload the core. Useful after schema changes.
        Be aware that you might need to re-ingest everything if there were changes to the indexing part of the schema."""
        return self.get_json(
            "admin/cores?action=RELOAD&core=" + self.core, use_core=False
        )

    def unload(self):
        """Unload the core."""
        return self.get_json(
            "admin/cores?action=UNLOAD&core=" + self.core, use_core=False
        )

    def swap(self, other_core):
        """Will swap this core with the given one (that means rename their references)

        :param other_core: the name of the other core that this will be swapped with."""
        return self.get_json(
            "admin/cores?action=SWAP&core=%s&other=%s" % (self.core, other_core),
            use_core=False,
        )

    def status(self, general=False):
        """Return status information about this core or the whole Solr server.

        :param general: If True return all information as provided by the server, otherwise just the status info
        from this core."""
        url_str = "admin/cores?action=STATUS"
        if not general:
            url_str += "&core=" + self.core
        response = self.get_json(url_str, use_core=False)
        if general:
            return response
        else:
            return response["status"][self.core]

    def clone(self, new_instance_dir, data_dir="data", copy_data=False):
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
        shutil.copytree(
            os.path.join(self.instance_dir, "conf"),
            os.path.join(new_instance_dir, "conf"),
        )
        if copy_data:
            shutil.copytree(
                os.path.join(self.instance_dir, self.data_dir),
                os.path.join(new_instance_dir, data_dir),
            )

    def delete(self, query):
        """Issue a delete command, there's no default query for this to avoid unintentional deletion."""
        self.post(dict(delete=dict(query=query)), auto_list=False)

    @staticmethod
    def _get_metadata_from_path(
        in_dir: Path,
        abort_on_errors: bool,
        allowed_suffixes: Tuple[str, ...],
        drs_type: Optional[str] = None,
    ) -> Iterator[Tuple[DRSFile, Dict[str, str]]]:
        if in_dir.is_file():
            iterator = [in_dir]
        else:
            iterator = dir_iter(in_dir)
        for file in iterator:
            if file.suffix not in allowed_suffixes:
                continue
            timestamp = file.stat().st_mtime
            try:
                drs_file = DRSFile.from_path(file, activity=drs_type)
            except (ValueError, FileNotFoundError) as e:
                if abort_on_errors:
                    raise e
                log.error(e.__str__())
                continue
            metadata = SolrCore.to_solr_dict(drs_file)
            metadata["timestamp"] = timestamp
            metadata["time"] = get_solr_time_range(metadata.pop("time", ""))
            yield drs_file, metadata

    def _del_file_pattern(self, file_pattern: Path, prefix: str = "file") -> None:
        """Delete all entries of the core."""
        file_pattern = Path(file_pattern).expanduser().absolute()
        # TODO: Better way to determine if we have a regex on board
        if file_pattern.is_dir():
            file_pattern /= "*"
        self.delete(f"{prefix}:\\{file_pattern}")

    @staticmethod
    def delete_entries(
        file_pattern: Path,
        host: Optional[str] = None,
        port: Optional[int] = None,
        prefix: str = "file",
    ) -> None:
        """Delete all corresponding entries the the solr server.

        Parameters:
        ----------
        file_pattern:
            The input directory which contains the files to be delted from the
            solr server
        host:
            The server hostname of the apache solr server.
        port:
            The host port number the apache solr server is listinig to.
        prefix:
            The prefix representing the data sotre, currently only posix file
            types are supported (file)
        """
        core_latest = SolrCore(core="latest", host=host, port=port)
        core_all_files = SolrCore(core=None, host=host, port=port)
        core_all_files._del_file_pattern(file_pattern)
        core_latest._del_file_pattern(file_pattern)

    @staticmethod
    def load_fs(
        input_dir: Path,
        drs_type: Optional[str] = None,
        chunk_size: int = 10000,
        suffix: Tuple[str, ...] = (".nc", ".grb", ".zarr", ".grib", ".nc4"),
        core: Optional[str] = None,
        core_latest: Optional[SolrCore] = None,
        core_all_files: Optional[SolrCore] = None,
        abort_on_errors: bool = False,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        """Load information of files on posix file system into Solr.

        This method loads the information from a file and decides if it should be added
        to just the common file core, holding the index of all files,
        or also to the *latest* core, holding information
        about the latest version of all files
        remember that in CMIP5 not all files are version, just the datasets).

        Parameters:
        -----------
        input_dir:
            Directory or input file that is crawled
        chunk_size:
            Number of entries that will be written to the Solr main core
             (the latest core will be flushed at the same time and is
             guaranteed to have at most as many as the other.)
        abort_on_errors:
            If dumping should get aborted as soon as an error is found,
            i.e. a file that can't be ingested. Most of the times there are many
            files being found in the dump file that are no data at all
        drs_type:
            Pre-define the data type to search for. If None (default) try
            guessing the type
        suffix:
            The file types that are taken into account when searching for data
        host:
            The server hostname of the apache solr server.
        port:
            The host port number the apache solr server is listinig to."""
        core_latest = core_latest or SolrCore(core="latest", host=host, port=port)
        core_all_files = core_all_files or SolrCore(core=core, host=host, port=port)
        core_latest._del_file_pattern(input_dir)
        core_all_files._del_file_pattern(input_dir)
        chunk, chunk_latest = [], []
        chunk_count = 0
        chunk_latest_new: Dict[str, Dict[str, str]] = {}
        latest_versions: Dict[str, str] = {}
        for (drs_file, metadata) in SolrCore._get_metadata_from_path(
            input_dir, abort_on_errors, suffix, drs_type=drs_type
        ):
            chunk.append(metadata)
            if drs_file.versioned:
                # TODO: We need a proper data set versioning.
                version = latest_versions.get(
                    drs_file.to_dataset(versioned=False), "-1"
                )
                idx = drs_file.to_dataset(versioned=False)
                if (drs_file.version or "0") > version:
                    # unknown or new version, update
                    version = drs_file.version or "0"
                    latest_versions[idx] = version
                    chunk_latest_new[idx] = metadata
                if (drs_file.version or "0") >= version:
                    chunk_latest.append(metadata)
            else:
                # if not version always add to latest
                chunk_latest_new[drs_file.to_dataset(versioned=False)] = metadata
                chunk_latest.append(metadata)
            if len(chunk) >= chunk_size:
                log.info(
                    "Sending entries %s-%s"
                    % (chunk_count * chunk_size, (chunk_count + 1) * chunk_size)
                )
                core_all_files.post(chunk)
                chunk = []
                chunk_count += 1
                if chunk_latest:
                    core_latest.post(chunk_latest)
                    chunk_latest, chunk_latest_new = [], {}
        # flush
        if len(chunk) > 0:
            log.info("Sending last %s entries" % (len(chunk)))
            core_all_files.post(chunk)
            if chunk_latest:
                core_latest.post(chunk_latest)

    @staticmethod
    def to_solr_dict(drs_file):
        """Extracts from a DRSFile the information that will be stored in Solr"""
        metadata = drs_file.dict["parts"].copy()
        metadata["file"] = drs_file.to_path()
        if "version" in metadata:
            metadata["file_no_version"] = metadata["file"].replace(
                "/%s/" % metadata["version"], "/"
            )
        else:
            metadata["file_no_version"] = metadata["file"]
        metadata["dataset"] = drs_file.drs_structure
        return metadata


def dir_iter(start_dir, abort_on_error=True, followlinks=True):
    for base_dir, dirs, files in os.walk(start_dir, followlinks=followlinks):
        # make sure we walk them in the proper order (latest version first)
        dirs.sort(reverse=True)
        files.sort(reverse=True)  # just for consistency
        for f in files:
            yield Path(base_dir) / f
