"""Freva commands for admins."""

from .solr import *
from .check import *
from .doc import *

__all__ = solr.__all__ + check.__all__ + doc.__all__  # type: ignore
