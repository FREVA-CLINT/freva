from collections import namedtuple
from datetime import datetime
from django.conf import settings
import django
from io import StringIO
import json
import os
import pytest
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time




class OutputWrapper:
    def __init__(self, ioStream):
        self.__buffer = StringIO()
        self.__original = ioStream
        self.capturing = False

    def write(self, s):
        if self.capturing:
            self.__buffer.write(s)
        self.__original.write(s)

    def writelines(self, strs):
        if self.capturing:
            self.__buffer.writelines(strs)
        self.__original.writelines( strs)

    def getvalue(self):
        return str(self.__buffer.getvalue()).replace('\x00', '')

    def reset(self):
        self.__buffer.truncate(0)

    def getOriginalStream(self):
        return self.__original

    def startCapturing(self):
        self.capturing = True

    def stopCapturing(self):
        self.capturing = False

    def __getattr__(self, *args, **kwargs):
        return self.__original.__getattribute__(*args, **kwargs)

@pytest.fixture(autouse=True, scope='session')
def dummy_env():

    test_conf = Path(__file__).absolute().parent / 'test.conf'
    env = os.environ.copy()
    os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = str(test_conf)
    yield os.environ
    os.environ = env

@pytest.fixture(scope='session')
def dummy_solr(dummy_env, dummy_settings):

    os.environ = dummy_env
    dummy_settings.reloadConfiguration()
    server = namedtuple('solr', ['solr_port',
                                          'solr_host',
                                          'all_files',
                                          'latest',
                                          'tmpdir',
                                          'drsfile',
                                          'files',
                                          'cmd',
                                          'DRSFILE'])
    server.solr_port = dummy_settings.get('solr.port')
    server.solr_host = dummy_settings.get('solr.host')
    from evaluation_system.model.solr_core import SolrCore
    from evaluation_system.model.solr import SolrFindFiles
    from evaluation_system.model.file import DRSFile, CMIP5
    from evaluation_system.misc.utils import supermakedirs
    server.all_files = SolrCore(core='files', host=server.solr_host, port=server.solr_port)
    server.latest = SolrCore(core='latest', host=server.solr_host, port=server.solr_port)
    print(server.solr_port, server.solr_host)
    with TemporaryDirectory(prefix='solr') as td:
        supermakedirs(str(Path(td) / 'solr_core'), 0o0777)
        server.tmpdir = str(Path(td) / 'solr_core')
        orig_dir = DRSFile.DRS_STRUCTURE[CMIP5]['root_dir']
        DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = server.tmpdir
        server.files = [
            'cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110719/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
            'cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110419/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc']
        for f in server.files:
            abs_path = Path(server.tmpdir) / f
            abs_path.parent.mkdir(exist_ok=True, parents=True)
            with abs_path.open('w') as f_out:
                f_out.write(' ')
        dump_file = str(Path(server.tmpdir) / 'dump1.csv')
        # add the files to solr
        SolrCore.dump_fs_to_file(str(Path(server.tmpdir) /  'cmip5'), dump_file)
        SolrCore.load_fs_from_file(
            dump_file, abort_on_errors=True,
            core_all_files=server.all_files, core_latest=server.latest
        )
        server.DRSFile = DRSFile
        yield server
    server.all_files.delete('*')
    server.latest.delete('*')
    DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = orig_dir

@pytest.fixture(scope='session')
def dummy_cmd(dummy_settings):

    from evaluation_system.commands import FrevaBaseCommand
    class DummyCommand(FrevaBaseCommand):
        __short_description__ = '''This is a test dummy'''
        __description__ = __short_description__

        _args = [
            {'name': '--debug', 'short': '-d', 'help': 'turn on debugging info and show stack trace on exceptions.',
             'action': 'store_true'},
            {'name': '--help', 'short': '-h', 'help': 'show this help message and exit', 'action': 'store_true'},
         {'name': '--input', 'help': 'Some input value', 'metavar': 'PATH'},
         ]

        def _run(self,*args,**kwargs):
            print('The answer is %s' % self.args.input)

    yield DummyCommand()

@pytest.fixture(autouse=True, scope='session')
def dummy_settings(dummy_env):
    # Application definition
    local_db = Path(__file__).absolute().parent / 'local.db'
    SETTINGS = {}
    SETTINGS['INSTALLED_APPS'] = (
        'django.contrib.auth',  # We need this to access user groups
        'django.contrib.flatpages'
    )
    SETTINGS['DATABASES'] = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(local_db)
        }
    }
    os.environ = dummy_env
    try:
        settings.configure(**SETTINGS)
    except RuntimeError:
        pass
    django.setup()
    from evaluation_system.misc import config
    yield config
    del os.environ[config._DEFAULT_ENV_CONFIG_FILE]
    config.reloadConfiguration()

@pytest.fixture(scope='module')
def broken_run(dummy_settings):

    from evaluation_system.commands.admin.check_4_broken_runs import Command
    from evaluation_system.api import plugin_manager as pm
    from evaluation_system.misc import config
    config.reloadConfiguration()
    pm.reloadPlugins()
    yield Command()

@pytest.fixture(scope='module')
def hist_obj():

    from evaluation_system.model.history.models import History
    from django.contrib.auth.models import User
    yield History.objects.create(
            status=History.processStatus.running,
            slurm_output='/some/out.txt',
            timestamp=datetime.now(),
            uid=User.objects.first()
        )

@pytest.fixture(scope='session')
def prog_name():
    return Path(sys.argv[0]).name

@pytest.fixture(scope='session')
def stderr():
    __original_stderr = sys.stderr
    sys.stderr = OutputWrapper(sys.stderr)
    yield sys.stderr
    sys.stderr = __original_stderr

@pytest.fixture(scope='session')
def stdout():
    __original_stdout = sys.stdout
    sys.stdout = OutputWrapper(sys.stdout)
    yield sys.stdout
    sys.stdout = __original_stdout
