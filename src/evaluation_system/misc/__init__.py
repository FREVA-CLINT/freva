import logging
import os
import sys

logging.basicConfig(format="%(name)s - %(levelname)s - %(message)s")
logger: logging.Logger = logging.getLogger("freva")
logger.setLevel(logging.INFO)

_DEFAULT_CONFIG_FILE_LOCATION = os.path.join(
    sys.prefix, "freva", "evaluation_system.conf"
)
# now check if we have a configuration file, and read the defaults from there
CONFIG_FILE = os.environ.get(
    "EVALUATION_SYSTEM_CONFIG_FILE", _DEFAULT_CONFIG_FILE_LOCATION
)
