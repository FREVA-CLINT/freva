"""General Freva commandline argument parser."""

import argcomplete
import argparse
import sys

import freva
from .utils import BaseCompleter, BaseParser, is_admin
from typing import Optional, List

COMMAND = "freva"
from evaluation_system.misc import config, logger


class ArgParser(BaseParser):
    """Cmd argument parser class for main entry-point."""

    def __init__(self, argv=None):

        sub_commands = (
            "databrowser",
            "plugin",
            "history",
            "crawl-my-data",
            "esgf",
        )
        epilog = f"""To get help for the individual sub-commands use:
        {COMMAND} <sub-command> --help
"""
        argv = argv or sys.argv[1:]
        admin_commands = ("solr", "check", "doc")
        if is_admin():
            sub_commands += admin_commands
        try:
            if argv[0] in sub_commands:
                argv[0] = argv[0].strip("-")
        except IndexError:
            argv.append("-h")
        self.parser = argparse.ArgumentParser(
            prog=COMMAND,
            epilog=epilog,
            description=f"Free EVAluation sysystem framework (freva)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self.call_parsers = []
        super().__init__(sub_commands)
        args = self.parse_args(argv)
        argcomplete.autocomplete(self.parser)
        try:
            args.apply_func(args, **self.kwargs)
        except KeyboardInterrupt:
            sys.exit(257)

    def parse_crawl_my_data(self):
        """Parse the user data crawl."""
        from .crawl_my_data import CrawlDataCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "crawl-my-data",
                description=CrawlDataCli.desc,
                help=CrawlDataCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = CrawlDataCli(COMMAND, self.call_parsers[-1])

    def parse_history(self):
        """Parse the history command."""
        from .history import HistoryCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "history",
                description=HistoryCli.desc,
                help=HistoryCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = HistoryCli(COMMAND, self.call_parsers[-1])

    def parse_plugin(self):
        """Parse the plugin command."""
        from .plugin import PluginCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "plugin",
                description=PluginCli.desc,
                help=PluginCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = PluginCli(COMMAND, self.call_parsers[-1])

    def parse_check(self):
        """Parse the check command."""
        from .admin.checks import CheckCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "check",
                description=CheckCli.desc,
                help=CheckCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = CheckCli(self.call_parsers[-1])

    def parse_solr(self):
        """Parse the solr index command."""
        from .admin.solr import SolrCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "solr",
                description=SolrCli.desc,
                help=SolrCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = SolrCli(self.call_parsers[-1])

    def parse_doc(self):
        """Parse the docu update command."""
        from .admin.doc import DocCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "doc",
                description=DocCli.desc,
                help=DocCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = DocCli(self.call_parsers[-1])

    def parse_esgf(self):
        """Parse the esgf command."""
        from .esgf import EsgfCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "esgf",
                description=EsgfCli.desc,
                help=EsgfCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = EsgfCli(COMMAND, self.call_parsers[-1])

    def parse_databrowser(self):
        """Parse the databrowser command."""
        from .databrowser import DataBrowserCli

        self.call_parsers.append(
            self.subparsers.add_parser(
                "databrowser",
                description=DataBrowserCli.desc,
                help=DataBrowserCli.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
        )
        _cli = DataBrowserCli(COMMAND, self.call_parsers[-1])


def main(argv: Optional[List[str]] = None) -> None:
    """Wrapper for entrypoint script."""
    ArgParser(argv or sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    main()
