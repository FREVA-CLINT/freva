import logging

logging.basicConfig(
    format="%(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)
logger: logging.Logger = logging.getLogger("freva")
