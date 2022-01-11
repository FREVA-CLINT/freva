"""General Freva commandline argument parser."""

import argparse
import sys

from .utils import BaseParser, is_admin
from typing import Optional, List

COMMAND = "freva"


class ArgParser(BaseParser):
    """Cmd argument parser class for main entry-point."""


    def __init__(self, argv: List[str]):

        epilog = f"""To get help for the individual sub-commands use:
        {COMMAND} <sub-command> --help
"""
        argv = argv or sys.argv[1:]
        sub_commands = self.get_subcommands()
        try:
            if argv[0] in sub_commands:
                argv[0] = argv[0].strip("-")
        except IndexError:
            argv.append("-h")
        parser = argparse.ArgumentParser(
            prog=COMMAND,
            epilog=epilog,
            description="Free EVAluation sysystem framework (freva)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self.call_parsers: List[argparse.ArgumentParser] = []
        super().__init__(sub_commands, parser)
        args = self.parse_args(argv)
        try:
            args.apply_func(args, **self.kwargs)
        except KeyboardInterrupt:
            sys.exit(130)

    def parse_crawl_my_data(self) -> None:
        """Parse the user data crawl."""
        from .crawl_my_data import CrawlDataCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "crawl-my-data",
                description=self.sub_commands["crawl-my-data"],
                help=self.sub_commands["crawl-my-data"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        CrawlDataCli(COMMAND, self.call_parsers[-1])

    def parse_history(self) -> None:
        """Parse the history command."""
        from .history import HistoryCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "history",
                description=self.sub_commands["history"],
                help=self.sub_commands["history"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        HistoryCli(COMMAND, self.call_parsers[-1])

    def parse_plugin(self) -> None:
        """Parse the plugin command."""
        from .plugin import PluginCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "plugin",
                description=self.sub_commands["plugin"],
                help=self.sub_commands["plugin"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        PluginCli(COMMAND, self.call_parsers[-1])

    def parse_check(self) -> None:
        """Parse the check command."""
        from .admin.check import CheckCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "check",
                description=self.sub_commands["check"],
                help=self.sub_commands["check"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        CheckCli(self.call_parsers[-1])

    def parse_solr(self) -> None:
        """Parse the solr index command."""
        from .admin.solr import SolrCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "solr",
                description=self.sub_commands["solr"],
                help=self.sub_commands["solr"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        SolrCli(self.call_parsers[-1])

    def parse_doc(self) -> None:
        """Parse the docu update command."""
        from .admin.doc import DocCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "doc",
                description=self.sub_commands["doc"],
                help=self.sub_commands["doc"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        DocCli(self.call_parsers[-1])

    def parse_esgf(self) -> None:
        """Parse the esgf command."""
        from .esgf import EsgfCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "esgf",
                description=self.sub_commands["esgf"],
                help=self.sub_commands["esgf"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        EsgfCli(COMMAND, self.call_parsers[-1])

    def parse_databrowser(self) -> None:
        """Parse the databrowser command."""
        from .databrowser import DataBrowserCli
        self.call_parsers.append(
            self.subparsers.add_parser(
                "databrowser",
                description=self.sub_commands["databrowser"],
                help=self.sub_commands["databrowser"],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        DataBrowserCli(COMMAND, self.call_parsers[-1])


def main(argv: Optional[List[str]] = None) -> None:
    """Wrapper for entrypoint script."""
    ArgParser(argv or sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    main()
