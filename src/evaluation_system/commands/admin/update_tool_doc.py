#!/usr/bin/env python

"""
update_tool_doc -- update the html code of tools

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
"""

from evaluation_system.commands import FrevaBaseCommand
from evaluation_system.misc import config
import logging, sys
from pathlib import Path
import os
import shutil
from tempfile import TemporaryDirectory
from subprocess import run, PIPE
import shlex
import re
from django.contrib.flatpages.models import FlatPage


class Command(FrevaBaseCommand):

    _args = [
             {'name': '--debug', 'short': '-d',
              'help': 'turn on debugging info and show stack trace on exceptions.', 'action': 'store_true'},
             {'name': '--help', 'short': '-h',
              'help': 'show this help message and exit', 'action': 'store_true'},
             {'name': '--docpath', 'help': 'path to doc folder with tex file'},
             {'name': '--tex_file', 'help': 'filename of main tex file'},
             {'name': '--tool', 'help': 'tool name'}
             ] 

    __short_description__ = '''Update the html files of tool documentation'''    

    def copy_and_overwrite(self, from_path, to_path):
        if os.path.exists(to_path):
            shutil.rmtree(to_path)
        if os.path.exists(from_path):
            shutil.copytree(from_path, to_path)    
            
    def _run(self):

        doc_path = self.args.docpath
        tex_file = self.args.tex_file
        tool = self.args.tool.lower()
        if not tex_file:
            print('Can\'t find a .tex file in this directory!')
            return
        file_root = tex_file.split('.')[0]
        # copy folder to /tmp for processing
        config.reloadConfiguration()
        with TemporaryDirectory() as td:
            new_path = Path(td) / tool
            self.copy_and_overwrite(doc_path, new_path)
            # change path and run "htlatex" and "bibtex"
            os.chdir(new_path)
            bibfiles = [str(f) for f in new_path.rglob('*.bib')]
            html_file = (new_path / tex_file).with_suffix('.html')
            pandoc = Path(sys.exec_prefix) / 'bin' / 'pandoc'
            cmd = f'{pandoc} {new_path / tex_file} -f latex -t html5'
            if bibfiles:
                cmd += f' --bibliography {bibfiles[0]}'
            cmd += f' -o {html_file}'
            res = run(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
            # open html file and remove <head> and <body> tags
            with html_file.open() as fi:
                text = fi.read()
            figure_prefix = 'figures'
            # replace img src
            text = text.replace('src="%s/' % figure_prefix,
                                'style="width:80%;" src="/static/preview/doc/'+tool+'/')
            # remove too big sigma symbols
            text = text.replace('mathsize="big"', '')
            flat_page, created = FlatPage.objects.get_or_create(
                title=self.args.tool, url='/about/%s/' % tool)
            #if created:
            #    print(flat_page).sites
            #    flat_page.sites = [1]
            flat_page.content = text
            flat_page.save()
            # Copy images to website preview path
            preview_path = config.get('preview_path')
            dest_dir = os.path.join(preview_path, 'doc/%s/' % tool)
            os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.copyfile('%s.css' % tool, os.path.join(dest_dir, '%s.css' % tool))
            except FileNotFoundError:
                pass
            print(f'Flat pages for {tool} has been created')

if __name__ == "__main__":
    Command().run()
