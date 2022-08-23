"""Collection of admin commands to create flat pages."""

from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import shlex
from subprocess import run, PIPE
import sys
from tempfile import TemporaryDirectory
from typing import Any, Optional

import lazy_import
import django
from evaluation_system.misc import logger
from ..utils import BaseParser


is_admin = lazy_import.lazy_function("freva.cli.utils.is_admin")
pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
config = lazy_import.lazy_module("evaluation_system.misc.config")

__all__ = ["update_tool_doc"]
CLI = "DocCli"


class Convert2Html:
    """Converter class that converts different file formats to html."""

    def __init__(self, input_file: Path, tmpdir: Path):

        self.tmpdir = tmpdir
        shutil.copytree(input_file.parent, self.tmpdir)
        self.input_file = tmpdir / input_file.name
        self.input_dir = tmpdir
        self.html_file = self.input_file.with_suffix(".html")
        suffix = Path(input_file).suffix.strip(".")
        self.conv_func = getattr(self, f"convert_{suffix}")

    def convert_tex(self) -> str:
        """Convert latex to html files."""
        bibfiles = [str(f) for f in self.input_dir.rglob("*.bib")]
        cmd = f"pandoc {self.input_file} -f latex -t html5"
        if bibfiles:
            cmd += f" --bibliography {bibfiles[0]}"
        cmd += f" -o {self.html_file}"
        return cmd

    def convert(self, tool: str) -> str:
        """Convert the input to html file."""
        cmd = self.conv_func()
        env = os.environ.copy()
        env["PATH"] = f"{Path(sys.exec_prefix) / 'bin'}:{env['PATH']}"
        _ = run(
            shlex.split(cmd),
            stdout=PIPE,
            stderr=PIPE,
            env=env,
            check=True,
            cwd=self.input_file.parent,
        )
        with self.html_file.open() as fi:
            text = fi.read()
        # replace img src
        text = text.replace(
            'src="figures/', 'style="width:80%;" src="/static/preview/doc/' + tool + "/"
        )
        # remove too big sigma symbols
        return text.replace('mathsize="big"', "")


def update_tool_doc(tool_name: str, master_doc: Optional[Path] = None) -> None:
    """Update the html files of tool documentation"""
    is_admin(raise_error=True)
    FlatPage = django.contrib.flatpages.models.FlatPage  # type: ignore
    plugin_path = Path(pm.get_plugin_instance(tool_name).class_basedir or ".")
    doc_file = Path(master_doc or plugin_path / "doc" / "{tool_name}.tex")
    if not doc_file.is_file():
        raise FileNotFoundError(f"No documentation found in {doc_file.parent}")
    tool = tool_name.lower()
    # copy folder to /tmp for processing
    config.reloadConfiguration()
    with TemporaryDirectory(prefix=tool, suffix="_doc") as td:
        conv = Convert2Html(doc_file, Path(td) / "doc")
        html_text = conv.convert(tool)
        flat_page, created = FlatPage.objects.get_or_create(
            title=tool_name, url=f"/about/{tool}/"
        )
        flat_page.content = html_text
        flat_page.save()
        # Copy images to website preview path
        preview_path = Path(config.get("preview_path"))
        dest_dir = preview_path / f"doc/{tool}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Flat pages for {tool_name} has been created")


class DocCli(BaseParser):
    """Interface defining parsers for documetation update."""

    desc = "Update the plugin documentation."

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        """Construct the sub arg. parser."""
        self.sub_commands = {}
        parser.add_argument("tool", help="Plugin name", type=str)
        parser.add_argument(
            "--file-name",
            help=(
                "Filename of the main docu file. Standard doc location "
                " is taken if None given (default)."
            ),
            default=None,
            type=Path,
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
    def run_cmd(args: argparse.Namespace, **kwargs: Any) -> None:
        """Apply the check4broken_runs method"""

        update_tool_doc(args.tool, args.file_name)
