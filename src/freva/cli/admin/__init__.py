"""Freva commands for admins."""

from .solr import *
from .checks import *
from .doc import *

__all__ = solr.__all__ + checks.__all__ + doc.__all__  # type: ignore
