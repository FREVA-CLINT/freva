import logging

logging.basicConfig(format="%(name)s - %(levelname)s - %(message)s")
logger: logging.Logger = logging.getLogger("freva")
logger.setLevel(logging.INFO)
