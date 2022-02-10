import time
import gzip
from datetime import datetime
from evaluation_system.model.esgf import P2P
from evaluation_system.misc import config
from esgf_crawl_config import Esgf2SolrConfig


class Esgf2Solr(object):
    def __init__(self, project, experiment, outpath, p2p=P2P()):
        self.project = {"project": project}
        self.experiment = experiment
        self.outpath = outpath
        self.show_facets = "experiment"

        self.facets = {"project": list(self.project.values())[0], "type": "File"}
        self.fields = [
            "title",
            "size",
            "project",
            "product",
            "institute",
            "model",
            "experiment",
            "time_frequency",
            "realm",
            "variable",
            "ensemble",
            "timestamp",
        ]
        self.prefix = "esgf-"
        self.prepath = config.get("project_data")

    def find_experiment(self, p2p=P2P()):
        results = p2p.get_facets(self.show_facets, **self.project)
        if len(results["experiment"].keys()) == 0:
            raise Exception("Experiment not found")
        self.experiments = results["experiment"].keys()

    def get_path(self, p2p=P2P()):
        gzname = self.outpath + "/solr_crawl_%s.csv.gz" % datetime.now().strftime(
            "%Y-%m-%d_%H%M%S"
        )
        try:
            with gzip.open(gzname, "wb", 6) as f:
                f.write(
                    "crawl_dir\t%s%s%s\n"
                    % (self.prepath, self.prefix, self.project["project"])
                )
                f.write("\n")
                f.write("data\n")
                for experiment in self.experiments:
                    if self.experiment is not None and experiment != self.experiment:
                        continue
                    facets = self.facets
                    facets.update({"experiment": experiment})
                    esgffiles = {}
                    for dataset in p2p.get_datasets(
                        fields=",".join(self.fields), **facets
                    ):
                        cmor_path = Esgf2SolrConfig().project_select(dataset)
                        filename = cmor_path["filename"]
                        esgfpath = "/".join(
                            (
                                self.prefix + cmor_path["project"],
                                cmor_path["product"],
                                cmor_path["institute"],
                                cmor_path["model"],
                                cmor_path["experiment"],
                                cmor_path["time_frequency"],
                                cmor_path["realm"],
                                cmor_path["cmor_var"],
                                cmor_path["ensemble"],
                            )
                        )
                        esgfpath += "/"
                        timestamp = time.mktime(
                            (
                                datetime.strptime(
                                    dataset["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
                                )
                            ).timetuple()
                        )
                        if self.prepath + esgfpath + filename not in esgffiles:
                            esgffiles[self.prepath + esgfpath + filename] = 0
                        if timestamp >= esgffiles[self.prepath + esgfpath + filename]:
                            esgffiles[self.prepath + esgfpath + filename] = timestamp
                    [f.write(key + ",%s\n" % value) for key, value in esgffiles.items()]
                f.close()
        except IOError:
            raise FileNotFoundError("Path does not exist")
