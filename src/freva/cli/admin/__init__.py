"""Freva commands for admins."""

from .solr import *
from .check import *

__all__ = solr.__all__ + check.__all__  # type: ignore
