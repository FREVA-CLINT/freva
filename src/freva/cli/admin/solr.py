"""Collection of admin commands for apache solr requests."""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any, Optional

import lazy_import
from ..utils import subparser_func_type, BaseParser, is_admin

SolrCore = lazy_import.lazy_class("evaluation_system.model.solr_core.SolrCore")
config = lazy_import.lazy_module("evaluation_system.misc.config")


__all__ = ["re_index", "del_index"]


CLI = "SolrCli"


def re_index(
    input_dir: Path,
    *,
    abort_on_errors: bool = False,
    chunk_size: int = 200,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """(Re)-Index data files on posix file system on the apache solr server.

    Parameters:
    ----------
        input_dir:
            The input directory that is crawled, can also be single files
        abort_on_errors:
            Do not keep ingesting data if it fails for one file
        chunk_size:
            Size of the chunks tht is ingested to the solr server
        host:
            The server hostname of the apache solr server.
        port:
            The host port number the apache solr server is listinig to.
    """
    is_admin(raise_error=True)
    solr_core = SolrCore(core="files")
    solr_core.load_fs(
        Path(input_dir).expanduser().absolute(),
        chunk_size=max(1, int(chunk_size)),
        abort_on_errors=abort_on_errors,
        host=host,
        port=port,
    )


def del_index(
    file_pattern: Path,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """Delete entries from solr server.

    Parameters:
    ----------
    file_pattern:
        Directory name/File name or Regex expression for entries that
        should be deleted
    host:
        The server hostname of the apache solr server.
    port:
        The host port number the apache solr server is listinig to.
    """
    is_admin(raise_error=True)
    solr_core = SolrCore(core="files")
    solr_core.delete_entries(file_pattern, host=host, port=port, prefix="file")


class SolrIndex(BaseParser):
    """Parser for indexing solr server data."""

    desc = "(Re)-Index data on the apache solr server."

    def __init__(self, parser: argparse.ArgumentParser):
        """Construct the parser for indexing data."""
        parser.add_argument(
            "input_dir",
            help="The input directory/file that needs to be (re)-indexed.",
            type=Path,
        )
        parser.add_argument(
            "--chunk-size",
            help="Request size that is submitted to solr server",
            default=200,
            type=int,
        )
        parser.add_argument("--abort-on-errors", action="store_true", default=False)
        parser.add_argument(
            "--delete",
            action="store_true",
            default=False,
            help="Delete entries instead of adding them",
        )
        parser.add_argument(
            "--host",
            type=str,
            default=config.get("solr.host"),
            help="Apache solr server hostname",
        )
        parser.add_argument(
            "--port",
            type=str,
            default=config.get("solr.port"),
            help="Host port the solr server is listning to",
        )
        self.parser = parser
        parser.add_argument(
            "--debug",
            "--verbose",
            help="Use verbose output.",
            action="store_true",
            default=False,
        )
        self.logger.setLevel(20)  # Set log level to info
        self.parser.set_defaults(apply_func=self.run_cmd)

    @staticmethod
    def run_cmd(
        args: argparse.Namespace, other_args: Optional[list[str]], **kwargs: Any
    ) -> None:
        """Reindex the data."""
        input_dir = kwargs.pop("input_dir")
        if kwargs.pop("delete"):
            return del_index(input_dir, port=kwargs["port"], host=kwargs["host"])
        re_index(input_dir, **kwargs)


class SolrCli(BaseParser):
    """Interface defining parsers for the solr core."""

    desc = "Apache solr server related sub-commands."

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        """Construct the sub arg. parser."""

        sub_commands: dict[str, subparser_func_type] = {"index": self.parse_index}
        super().__init__(sub_commands, parser)
        # This parser doesn't do anything without a sub-commands
        # hence the default function should just print the usage
        self.parser.set_defaults(apply_func=self._usage)

    @staticmethod
    def parse_index(subparsers: argparse._SubParsersAction) -> SolrIndex:
        sub_parser = subparsers.add_parser(
            "index",
            description="(Re)-Index data on the apache solr server.",
            help="(Re)-Index data on the apache solr server.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        return SolrIndex(sub_parser)
