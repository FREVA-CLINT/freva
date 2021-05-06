from collections import namedtuple
from datetime import datetime
from django.conf import settings
import django
from io import StringIO
import importlib
import json
import os
import pytest
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory, NamedTemporaryFile
import time


# The following is a recipe by 'Ciro Santilli TRUMP BAN IS BAD'
# which was taken from stackoverflow 
#(https://stackoverflow.com/questions/19009932/import-arbitrary-python-source-file-python-3-3#19011259)
def import_path(path):
    module_name = os.path.basename(path).replace('-', '_')
    spec = importlib.util.spec_from_loader(
        module_name,
        importlib.machinery.SourceFileLoader(module_name, str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module



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

@pytest.fixture(scope='session')
def dummy_env():

    test_conf = Path(__file__).absolute().parent / 'test.conf'
    env = os.environ.copy()
    os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = str(test_conf)
    yield os.environ
    os.environ = env

@pytest.fixture(scope='module')
def dummy_pr(dummy_env, dummy_settings):

    from evaluation_system.commands.admin.process_pull_requests import Command
    from evaluation_system.api import plugin_manager as pm
    pm.reloadPlugins()
    dummy_settings.reloadConfiguration()
    yield Command()

@pytest.fixture(scope='module')
def dummy_git_path():
    with TemporaryDirectory(prefix='git') as td:
        repo_path = Path(td) / 'test_plugin.git'
        tool_path = Path(td) / 'test_tool'
        yield repo_path, tool_path

@pytest.fixture(scope='module')
def temp_dir():
    with TemporaryDirectory() as td:
        yield Path(td)

@pytest.fixture(scope='module')
def dummy_crawl(dummy_solr, dummy_settings, dummy_env):

    from evaluation_system.model.solr_models.models import UserCrawl
    # At this point files have been ingested into the server already,
    # delete them again
    [getattr(dummy_solr, key).delete('*') for key in ('all_files', 'latest')]
    yield dummy_solr
    UserCrawl.objects.all().delete()

@pytest.fixture(scope='session')
def dummy_solr(dummy_env, dummy_settings):

    dummy_settings.reloadConfiguration()
    server = namedtuple('solr', ['solr_port',
                                  'solr_host',
                                  'all_files',
                                  'latest',
                                  'tmpdir',
                                  'drsfile',
                                  'files',
                                  'cmd',
                                  'dump_file'
                                  'DRSFILE'])
    server.solr_port = dummy_settings.get('solr.port')
    server.solr_host = dummy_settings.get('solr.host')
    from evaluation_system.model.solr_core import SolrCore
    from evaluation_system.model.solr import SolrFindFiles
    from evaluation_system.model.file import DRSFile, CMIP5
    from evaluation_system.misc.utils import supermakedirs
    server.all_files = SolrCore(core='files', host=server.solr_host, port=server.solr_port)
    server.latest = SolrCore(core='latest', host=server.solr_host, port=server.solr_port)
    server.all_files.delete('*')
    server.latest.delete('*')
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
        server.dump_file = dump_file
        server.DRSFile = DRSFile
        server.fn = str(Path(server.tmpdir) / server.files[0])
        server.drs = server.DRSFile.from_path(server.fn)
        yield server
    try:
        server.all_files.delete('*')
        server.latest.delete('*')
    except:
        pass
    DRSFile.DRS_STRUCTURE[CMIP5]['root_dir'] = orig_dir

@pytest.fixture(scope='module')
def dummy_config(dummy_env, dummy_settings_single):

    from evaluation_system.misc import config, utils
    config.reloadConfiguration()
    yield config
    config.reloadConfiguration()

@pytest.fixture(scope='module')
def dummy_plugin(dummy_env, dummy_settings):

    from evaluation_system.tests.mocks.dummy import DummyPlugin
    yield DummyPlugin()

@pytest.fixture(scope='function')
def dummy_history(dummy_env, dummy_settings):

    from evaluation_system.model.history.models import History
    yield History
    History.objects.all().delete()

@pytest.fixture(scope='function')
def plugin_command(dummy_settings, dummy_env):

    from evaluation_system.misc import config
    from evaluation_system.api import plugin_manager as pm
    from evaluation_system.commands.plugin import Command
    config.reloadConfiguration()
    pm.reloadPlugins()
    yield Command()
    config.reloadConfiguration()
    pm.reloadPlugins()

@pytest.fixture(scope='module')
def test_user(dummy_env, dummy_settings, config_dict):

    from evaluation_system.model.history.models import History
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='test_user2', password='123')
    hist = History.objects.create(
            timestamp=datetime.now(),
            status=History.processStatus.running,
            uid=user,
            configuration='{"some": "config", "dict": "values"}',
            tool='dummytool',
            slurm_output='/path/to/slurm-44742.out'
        )
    yield user, hist
    user.delete()
    hist

@pytest.fixture(scope='function')
def temp_user(dummy_settings):
    from evaluation_system.tests.mocks.dummy import DummyUser
    with DummyUser(random_home=True, pw_name='someone') as user:
        yield user

@pytest.fixture(scope='function')
def dummy_user(dummy_env, dummy_settings, config_dict, dummy_plugin, dummy_history, temp_user):

    from django.contrib.auth.models import User
    User.objects.filter(username='test_user2').delete()
    user_entry = namedtuple('test_user2', ['user', 'row_id'])
    user_entry.user = temp_user
    user_entry.row_id = temp_user.getUserDB().storeHistory(
        dummy_plugin,
        config_dict, 'test_user2',
        dummy_history.processStatus.not_scheduled,
        caption='My caption')
    yield user_entry
    User.objects.filter(username='test_user2').delete()



@pytest.fixture(scope='module')
def config_dict():
    yield {'the_number': 42,
            'number': 12,
            'something': 'else',
            'other': 'value',
            'input': '/folder'}

@pytest.fixture(scope='module')
def tmp_dir():
    with TemporaryDirectory(prefix='freva_test_') as td:
        yield Path(td)
        [f.unlink() for f in Path(td).rglob('*.*')]



@pytest.fixture(scope='module')
def search_dict():
    yield {'variable': 'tas',
           'project': 'CMIP5',
           'product': 'output1',
           'time_frequency': 'mon',
           'experiment': 'decadal2000',
           'model': 'MPI-ESM-LR',
           'ensemble': 'r1i1p1',
           }

@pytest.fixture(scope='module')
def esgf_command():
    from evaluation_system.commands.esgf import Command
    yield Command()




@pytest.fixture(scope='module')
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

@pytest.fixture(scope='module')
def dummy_settings_single(dummy_env):
    # Application definition
    import evaluation_system.settings.database
    from evaluation_system.misc import config
    yield config
    config.reloadConfiguration()

@pytest.fixture(scope='session')
def dummy_settings(dummy_env):
    from evaluation_system.misc import config
    import evaluation_system.settings.database
    yield config
    config.reloadConfiguration()

@pytest.fixture(scope='module')
def broken_run(dummy_settings):

    from evaluation_system.commands.admin.check_4_broken_runs import Command
    from evaluation_system.api import plugin_manager as pm
    from evaluation_system.misc import config
    config.reloadConfiguration()
    pm.reloadPlugins()
    yield Command()
    config.reloadConfiguration()
    pm.reloadPlugins()

@pytest.fixture(scope='module')
def hist_obj():

    from evaluation_system.model.history.models import History
    from django.contrib.auth.models import User
    from evaluation_system.misc import config
    yield History.objects.create(
            status=History.processStatus.running,
            slurm_output='/some/out.txt',
            timestamp=datetime.now(),
            uid=User.objects.first()
        )
    config.reloadConfiguration()

@pytest.fixture(scope='module')
def freva_lib(dummy_env, dummy_settings):
    sys.dont_write_bytecode = True
    freva_bin = list(Path(__file__).parents)[3] / 'bin' / 'freva'
    Freva = import_path(freva_bin)
    yield Freva.Freva()
    import evaluation_system.api.plugin_manager as pm
    pm.reloadPlugins()

@pytest.fixture(scope='module')
def prog_name():
    return Path(sys.argv[0]).name

@pytest.fixture(scope='module')
def stderr():
    __original_stderr = sys.stderr
    sys.stderr = OutputWrapper(sys.stderr)
    yield sys.stderr
    sys.stderr = __original_stderr

@pytest.fixture(scope='module')
def stdout():
    from evaluation_system.misc import config
    __original_stdout = sys.stdout
    sys.stdout = OutputWrapper(sys.stdout)
    yield sys.stdout
    sys.stdout = __original_stdout
    config.reloadConfiguration()
