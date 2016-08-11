#!/usr/bin/env python

'''
update_tool_doc -- update the html code of tools

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
'''

from evaluation_system.commands import (BaseCommand, CommandError,
                                        FrevaBaseCommand)
from evaluation_system.misc import config
import logging, sys
import os
import shutil
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
        shutil.copytree(from_path, to_path)    
            
    def _run(self):

        doc_path = self.args.docpath
        tex_file = self.args.tex_file
        #doc_path = 
        tool = self.args.tool.lower()
        # find .tex file 
        #tex_file = None
        #file_root = tex_file.split('.')[0] 
        #for fn in os.listdir(doc_path):
        #    if fn.endswith('.tex'):
        #        tex_file = fn
        #        file_root = tex_file.split('.')[0]
        #    elif fn.endswith('.bib'):
        #        bib_file = fn
        if not tex_file:
            print 'Can\'t find a .tex file in this directory!'
            return
        file_root = tex_file.split('.')[0]
        #copy folder to /tmp for processing
        new_path = '/tmp/%s/' % tool
        self.copy_and_overwrite(doc_path, new_path)
        
        # change path and run "htlatex" and "bibtex"
        os.chdir(new_path)
        #cfg_file = '/home/illing/documentation/ht5mjlatex.cfg'
        cfg_file = os.path.dirname(__file__)+'/../../../../etc/ht5mjlatex.cfg' 
        os.system('htlatex %s "%s"' % (new_path+tex_file, cfg_file))
        os.system('bibtex %s' % file_root)
        os.system('htlatex %s "%s"' % (new_path+tex_file, cfg_file))
         
        # open html file and remove <head> and <body> tags
        fi = open(os.path.join(new_path, file_root+'.html'))
        text = fi.read()
        text = re.sub("<head>.*?</head>", "", text, flags=re.DOTALL)
        text = text.replace('</html>', '')
        text = text.replace('<html>', '')
        text = text.replace('</body>', '')
        text = text.replace('<body>', '')
        
        figure_prefix = 'figures'
        # replace img src
        text = text.replace('src="%s/' % figure_prefix,
                            'style="width:80%;" src="/static/preview/doc/'+tool+'/')
        #text = text.replace('src="%s/' % figure_prefix,
        #                    'src="/static/preview/doc/'+tool+'/')

        # remove too big sigma symbols
        text = text.replace('mathsize="big"', '')
        
        flat_page, created = FlatPage.objects.get_or_create(
            title=self.args.tool, url='/about/%s/' % tool
        )
        if created:
            flat_page.sites = [1]
        flat_page.content = text
        flat_page.save()
        
        # Copy images to website preview path
        preview_path = config.get('preview_path')
        self.copy_and_overwrite('%s/' % figure_prefix, os.path.join(preview_path, 'doc/%s/' % tool))
        # remove tmp files
        shutil.rmtree(new_path)
        
        
if __name__ == "__main__":
    Command().run()
