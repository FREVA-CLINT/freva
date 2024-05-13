"""Ingest dummy data into the solr server."""

import logging
import sys
from pathlib import Path

from evaluation_system.misc import config, logger
from evaluation_system.model.solr_core import SolrCore

if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    config.reloadConfiguration()
    if sys.argv[1:]:
        inp_data = Path(sys.argv[1])
    else:
        inp_data = Path(".").absolute() / ".docker" / "data"
    SolrCore.load_fs(inp_data, abort_on_errors=True)
