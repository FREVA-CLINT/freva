#!/usr/bin/env python

"""
solr_ingest -- manage crawling and ingesting files

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
"""

from evaluation_system.commands import CommandError, FrevaBaseCommand
from evaluation_system.model.solr_core import SolrCore
import sys
from evaluation_system.model.solr_models.models import UserCrawl
from evaluation_system.model.user import User


class Command(FrevaBaseCommand):

    _args = [
             {'name': '--debug', 'short': '-d', 'help': 'turn on debugging info and show stack trace on exceptions.',
              'action': 'store_true'},
             {'name': '--help', 'short': '-h', 'help': 'show this help message and exit', 'action': 'store_true'},
             {'name': '--crawl', 'help': 'crawl the given directory', 'metavar': 'PATH'},
             {'name': '--ingest', 'help': 'ingest the given file (as created by crawl)', 'metavar': 'FILE'},
             {'name': '--batch-size', 'help': 'Number of entries to send at the same time to Solr.', 'type': 'int',
              'metavar': 'N', 'default': 10000},
             {'name': '--solr-url', 'help': 'url to solr instance'},
             {'name': '--output', 'help': 'Instead of ingesting into Solr write to this file', 'metavar': 'FILE'},
             ] 

    __short_description__ = '''Command to ingest files to solr or dump crawl to file'''    

    def handle_exceptions(self, e):
        if hasattr(self, 'ingest_file'):
            try:
                crawl = UserCrawl.objects.get(tar_file=self.ingest_file.split('/')[-1])
                crawl.status = 'failed'
                crawl.ingest_msg = crawl.ingest_msg + '\n \n' + str(e) + '\nIngesting failed. Please check your directory structure.'
                crawl.save()
            except:
                pass

    def _run(self):
        # defaults
        batch_size = self.args.batch_size
        crawl_dir = self.args.crawl
        ingest_file = self.args.ingest
        abort_on_errors = self.DEBUG
        output = self.args.output
        solr_url = self.args.solr_url

        host = None
        port = None
        if self.args.solr_url is not None:
            import re
            mo = re.match('(?:https?://)?([^:/]{1,})(?::([0-9]{1,}))?(?:/.*|$)', solr_url)
            if not mo:
                raise Exception("Cannot understand the solr-url %s" % solr_url)
            host = mo.group(1)
            port = int(mo.group(2))
        
        if crawl_dir is None and ingest_file is None:
            raise CommandError('You must either crawl to generate a dump file or ingest it')
         
        # flush stderr in case we have something pending
        sys.stderr.flush()
        
        if host:
            core_files = SolrCore(core='files', host=host, port=port)
            core_latest = SolrCore(core='latest', host=host, port=port)

        if crawl_dir:
            if not output:
                raise Exception("You need to dump a file")
            SolrCore.dump_fs_to_file(crawl_dir, output, batch_size=batch_size, abort_on_errors=abort_on_errors)
            # create database entry
            user = User()
            db = user.getUserDB()
            UserCrawl.objects.create(status='crawling', path_to_crawl=crawl_dir, user_id=db.getUserId(user.getName()),
                                     tar_file=output.split('/')[-1])
        elif ingest_file:
            self.ingest_file = ingest_file
            from evaluation_system.misc.utils import capture_stdout
            fn = ingest_file.split('/')[-1]
            UserCrawl.objects.filter(tar_file=fn).update(status='ingesting')
            with capture_stdout() as capture:
                # Ingest the files!
                if host:
                    SolrCore.load_fs_from_file(dump_file=ingest_file, batch_size=batch_size,
                                               abort_on_errors=abort_on_errors, core_all_files=core_files,
                                               core_latest=core_latest)
                else:
                    SolrCore.load_fs_from_file(dump_file=ingest_file, batch_size=batch_size,
                                               abort_on_errors=abort_on_errors)
            print capture.result
            try:
                crawl = UserCrawl.objects.get(tar_file=fn)
                crawl.ingest_msg = crawl.ingest_msg + '\n' + capture.result + '\n\nNow you can find your data using "solr_search"'
                crawl.status = 'success'
                crawl.save()
            except:  # pragma nocover
                pass       

if __name__ == "__main__":  # pragma nocover
    Command().run()
