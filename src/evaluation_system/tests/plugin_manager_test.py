"""
Created on 31.05.2016

@author: Sebastian Illing
"""
import os
from pathlib import Path
import tempfile
import shutil
import logging
import re
import time
import datetime
import getpass
from tempfile import TemporaryDirectory
import pytest
# logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def test_modules(dummy_settings):
    import evaluation_system.api.plugin_manager as pm
    pm.reloadPlugins()
    pmod = pm.__plugin_modules_user__
    assert pmod is not None
    assert len(pmod) > 0

def test_plugins(dummy_settings, temp_user):
    from evaluation_system.tests.mocks.dummy import DummyPlugin, DummyUser
    import evaluation_system.api.plugin_manager as pm
    # force reload to be sure the dummy is loaded
    assert len(pm.getPlugins()) > 0
    assert 'dummyplugin' in pm.getPlugins()
    dummy = pm.getPluginDict('dummyplugin')
    assert dummy['description'] == DummyPlugin.__short_description__
    assert dummy['plugin_class'] == 'DummyPlugin'
    os.environ[f'EVALUATION_SYSTEM_PLUGINS_{temp_user.getName()}'] = f"{str(Path(__file__).parent / 'mocks')},dummy"
    pm.reloadPlugins(temp_user.getName())
    os.environ.pop(f'EVALUATION_SYSTEM_PLUGINS_{temp_user.getName()}')

def testDefaultPluginConfigStorage(temp_user):
    import evaluation_system.api.plugin_manager as pm
    pm.reloadPlugins(temp_user.username)
    home = temp_user.getUserHome()
    assert os.path.isdir(home)
    conf_file = pm.writeSetup('dummyplugin', user=temp_user)
    assert os.path.isfile(conf_file)

def test_plugin_config_storage(dummy_settings, temp_user):
    #from evaluation_system.tests.mocks.dummy import DummyPlugin, DummyUser
    import evaluation_system.api.plugin_manager as pm
    from evaluation_system.api.parameters import ValidationError
    #user = DummyUser(random_home=True, pw_name='test_user')
    home = temp_user.getUserHome()
    assert os.path.isdir(home)

    res = pm.getPluginInstance('dummyplugin').setupConfiguration(config_dict=dict(the_number=42))
    assert res['something'] == 'test'

    # write down this default
    conf_file = pm.writeSetup('dummyplugin', config_dict=dict(the_number=42), user=temp_user)

    assert os.path.isfile(conf_file)
    with open(conf_file, 'r') as f:
        config = f.read()

    assert '\nsomething=test\n' in config

    with pytest.raises(ValidationError):
        pm.parseArguments('dummyplugin', [])
    with pytest.raises(ValidationError):
        pm.parseArguments('dummyplugin', [], user=temp_user)
    res = pm.parseArguments('dummyplugin', [], use_user_defaults=True, user=temp_user)

    assert res == {'other': 1.4, 'number': None, 'the_number': 42, 'something': 'test', 'input': None}
    assert res['something'] == 'test'

    # now change the stored configuration
    config = config.replace('\nsomething=test\n', '\nsomething=super_test\n')
    with open(conf_file, 'w') as f:
        f.write(config)
    res = pm.parseArguments('dummyplugin', [], use_user_defaults=True, user=temp_user)
    assert res['something'] == 'super_test'

def test_parse_arguments(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm
    home = temp_user.getUserHome()
    assert os.path.isdir(home)

    # direct parsing
    for args, result in [("the_number=4", {'other': 1.3999999999999999, 'the_number': 4, 'something': 'test'})]:
        d = pm.parseArguments('Dummyplugin', args.split(), user=temp_user)
        assert d == result

    # parsing requesting user default but without any
    for args, result in [("the_number=4", {'other': 1.3999999999999999, 'the_number': 4, 'something': 'test'})]:
        d = pm.parseArguments('Dummyplugin', args.split(), user=temp_user)
        assert d == result

    pm.writeSetup('DummyPlugin', dict(number=7, the_number=42), temp_user)
    for args, result in [("number=4", dict(number=4, the_number=42, something='test', other=1.4, input=None))]:
        d = pm.parseArguments('Dummyplugin', args.split(), use_user_defaults=True, user=temp_user)
        assert d == result

    if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
        # make sure the home is a temporary one!!!
        shutil.rmtree(home)

def test_write_setup(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm
    home = temp_user.getUserHome()
    f = pm.writeSetup('DummyPlugin', dict(number="$the_number", the_number=42), temp_user)

    with open(f) as fp:
        num_line = [line for line in fp.read().splitlines() if line.startswith('number')][0]
        assert num_line == 'number=$the_number'

def test_get_history(dummy_settings, temp_user):
    import evaluation_system.api.plugin_manager as pm
    pm.writeSetup('DummyPlugin', dict(the_number=777), temp_user)
    pm.runTool('dummyplugin', user=temp_user)
    # DummyPlugin._runs.pop()

    res = pm.getHistory(user=temp_user)
    # self.assertEqual(len(res), 1)
    res = res[0]
    import re
    mo = re.search('^([0-9]{1,})[)] ([^ ]{1,}) ([^ ]{1,}) ([^ ]{1,})', res.__str__(compact=False))
    assert mo is not None
    g1 = mo.groups()
    assert all([g is not None for g in g1])
    mo = re.search('^([0-9]{1,})[)] ([^ ]{1,}) ([^ ]{1,})', res.__str__())
    g2 = mo.groups()
    assert all([g is not None for g in g2])
    assert g1[0] == g2[0]

def testDynamicPluginLoading(dummy_env, temp_user):
    import evaluation_system.api.plugin_manager as pm
    basic_plugin = """
from sys import modules
plugin = modules['evaluation_system.api.plugin']
parameters = modules['evaluation_system.api.parameters']

class %s(plugin.PluginAbstract):
__short_description__ = "Test"
__version__ = (0,0,1)
__parameters__ =  parameters.ParameterDictionary(
                                parameters.File(name="output", default="/tmp/file", help='output'),
                                parameters.File(name="input", mandatory=True, help="some input"))

def runTool(self, config_dict=None):
    print("%s", config_dict)"""

    with tempfile.TemporaryDirectory(prefix='dyn_plugin') as path1:
        os.makedirs(os.path.join(path1, 'a/b'))
        with open(path1 + '/a/__init__.py', 'w'):
            pass
        with open(path1 + '/a/blah.py', 'w') as f:
            f.write(basic_plugin % tuple(['TestPlugin1']*2))

        with tempfile.TemporaryDirectory(prefix='dyn_plugin') as path2:

            os.makedirs(os.path.join(path2, 'x/y/z'))
            with open(path2 + '/x/__init__.py', 'w'):
                pass
            with open(path2 + '/x/foo.py', 'w') as f:
                f.write(basic_plugin % tuple(['TestPlugin2']*2))

            os.environ[pm.PLUGIN_ENV] = '%s,%s:%s,%s' % \
                ('~/../../../../../..' + path1+'/a', 'blah',  # test a relative path starting from ~
                 '$HOME/../../../../../..' + path2+'/x', 'foo')  # test a relative path starting from $HOME
            log.debug('pre-loading: %s', list(pm.getPlugins()))

            assert 'testplugin1' not in list(pm.getPlugins())
            assert 'testplugin2' not in list(pm.getPlugins())
            pm.reloadPlugins()
            log.debug('post-loading: %s', list(pm.getPlugins()))
            assert 'testplugin1' in list(pm.getPlugins())
            assert 'testplugin2' in list(pm.getPlugins())

def test_get_plugin_dict(dummy_env):
    import evaluation_system.api.plugin_manager as pm
    with pytest.raises(pm.PluginManagerException):
        pm.getPluginDict('Not available')
    pl = pm.getPluginDict('DummyPlugin')
    assert isinstance(pl, dict)
    assert pl['plugin_class'] == 'DummyPlugin'

def test_preview_generation(dummy_env):
    import evaluation_system.api.plugin_manager as pm
    import evaluation_system.misc.config as config
    with tempfile.TemporaryDirectory() as td:
        d = str(Path(td) / 'tmp.pdf')
        s = os.path.dirname(__file__)+'/test_output/vecap_test_output.pdf'
        pm._preview_copy(s, d)
        assert os.path.isfile(d)
    with tempfile.TemporaryDirectory() as td:
        d = str(Path(td) / 'tmp.png')
        s = os.path.dirname(__file__) + '/test_output/test_image.png'
        f = open(d, 'w')
        f.close()
        pm._preview_copy(s, d)
        assert os.path.isfile(d)
    with tempfile.TemporaryDirectory() as td:
        d = str(Path(td) / 'tmp.png')
        s = os.path.dirname(__file__) + '/test_output/test_image.png'
        pm._preview_convert(s, d)
        assert os.path.isfile(d)

    r = pm._preview_generate_name('dummy', 'old_fn', {})
    assert 'dummy' in r
    assert len(r) == 14
    ts = time.time()
    r = pm._preview_generate_name('murcss', 'old_fn', {'timestamp': ts})
    assert 'murcss' in r
    assert datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d_%H%M%S') in r

    u = pm._preview_unique_file('murcss', 'old_fn', 'pdf', {'timestamp': ts})
    assert datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d_%H%M%S') in u
    assert 'murcss' in u
    assert config.get('preview_path') in u

    r1 = os.path.dirname(__file__) + '/test_output/vecap_test_output.pdf'
    r2 = os.path.dirname(__file__) + '/test_output/test_image.png'
    result = {r1: {'todo': 'copy'},
              r2: {'todo': 'convert'}}
    res = pm._preview_create('murcss', result)
    for r in res:
        assert os.path.isfile(r)
        os.remove(r)

def test_get_command_string(dummy_env, django_user):
    from evaluation_system.model.history.models import History
    import evaluation_system.api.plugin_manager as pm
    h = History.objects.create(
        timestamp=datetime.datetime.now(),
        status=History.processStatus.running,
        uid=django_user,
        configuration='{"some": "config", "dict": "values"}',
        tool='dummytool',
        slurm_output='/path/to/slurm-44742.out'
    )

    cmd = pm.getCommandString(h.id)
    assert 'freva --plugin' in cmd
    assert h.tool in cmd

def test_load_scheduled_conf(dummy_env, django_user, temp_user):
    from evaluation_system.model.history.models import History
    import evaluation_system.api.plugin_manager as pm
    h = History.objects.create(
        timestamp=datetime.datetime.now(),
        status=History.processStatus.scheduled,
        uid=django_user,
        configuration='{"some": "config", "dict": "values"}',
        tool='dummytool',
        slurm_output='/path/to/slurm-44742.out'
    )

    res = pm.loadScheduledConf('dummytool', h.id, temp_user)
    assert res == {}

def test_2dict_to_conf(dummy_env, dummy_plugin):

    import evaluation_system.api.plugin_manager as pm
    configuration={"number": 1, "the_number": 2, 'something': 'test'}
    with pytest.raises(pm.PluginManagerException):
        pm.dict2conf('dummytool', configuration)
    with pytest.raises(pm.ParameterNotFoundError):
        pm.dict2conf('dummyplugin', {'some':'config'})
    dd = pm.dict2conf('dummyplugin', configuration)
    assert isinstance(dd, list)
    assert len(dd) == len(configuration)

def test_scheduletool(dummy_env, dummy_plugin):
    import evaluation_system.api.plugin_manager as pm
    
    with TemporaryDirectory() as td:
        pm.scheduleTool('dummyplugin', slurmoutdir=str(Path(td) / 'tmp'))
