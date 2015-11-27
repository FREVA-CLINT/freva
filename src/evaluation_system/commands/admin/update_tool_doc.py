#!/usr/bin/env python

'''
update_tool_doc -- update the html code of tools

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
'''

from evaluation_system.commands import (BaseCommand, CommandError,
                                        FrevaBaseCommand)
import logging, sys
import os
import shutil
import re

class Command(FrevaBaseCommand):

    _args = [
             {'name': '--debug', 'short': '-d',
              'help': 'turn on debugging info and show stack trace on exceptions.', 'action': 'store_true'},
             {'name': '--help', 'short': '-h',
              'help': 'show this help message and exit', 'action': 'store_true'},
             {'name': '--docpath', 'help': 'path to doc folder with tex file'}
             ] 

    __short_description__ = '''Update the html files of tool documentation'''    
            
    
    def copy_and_overwrite(self, from_path, to_path):
        if os.path.exists(to_path):
            shutil.rmtree(to_path)
        shutil.copytree(from_path, to_path)    
            
    def _run(self):
        doc_path = self.args.docpath
        
        # find .tex file 
        tex_file = None
        for fn in os.listdir(doc_path):
            if fn.endswith('.tex'):
                tex_file = fn
                file_root = tex_file.split('.')[0]
            elif fn.endswith('.bib'):
                bib_file = fn
        if not tex_file:
            # TODO: raise an error
            return
        
        #copy folder to /tmp for processing
        new_path = '/tmp/blocking/'
        self.copy_and_overwrite(doc_path, new_path)
        
        # change path and run "htlatex" and "bibtex"
        os.chdir(new_path)
        cfg_file = '/home/illing/documentation/ht5mjlatex.cfg'
        os.system('htlatex %s "%s"' % (new_path+tex_file, cfg_file))
        os.system('bibtex %s' % file_root)
        os.system('htlatex %s "%s"' % (new_path+tex_file, cfg_file))
        
        # open html file and remove <head> and <body> tags
        fi = open(os.path.join(new_path, file_root+'.html'))
        text = fi.read()
        text = re.sub("<head>.*?</head>", "", text, flags=re.DOTALL)
        # TODO: should probably be don with regex
        text = text.replace('</html>', '')
        text = text.replace('<html>', '')
        text = text.replace('</body>', '')
        text = text.replace('<body>', '')
        
        print text
        
        
if __name__ == "__main__":
    Command().run()
