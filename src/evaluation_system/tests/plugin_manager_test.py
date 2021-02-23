"""
Created on 31.05.2016

@author: Sebastian Illing
"""
import unittest
import os
import tempfile
import shutil
import logging
import re
import time
import datetime
import getpass

from evaluation_system.api.parameters import ValidationError

import evaluation_system.misc.config as config
from evaluation_system.api.plugin import ConfigurationError
from evaluation_system.tests.mocks.dummy import DummyPlugin, DummyUser
from evaluation_system.model.history.models import History
from django.contrib.auth.models import User
import pytest
# logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

import evaluation_system.api.plugin_manager as pm

class Test(unittest.TestCase):

    def setUp(self):
        # this gets overwritten by the nosetest framework (it reloads all modules again)
        # we have to reset it every time.
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        config.reloadConfiguration()
        self.user = DummyUser(random_home=True, pw_name='test_user')
        pm.reloadPlugins(self.user.getName())
        self.user_django, created = User.objects.get_or_create(username=self.user.getName())

    def tearDown(self):
        User.objects.filter(username=self.user.getName()).delete()
        History.objects.all().delete()
        del os.environ['EVALUATION_SYSTEM_CONFIG_FILE']

    def test_modules(self):
        pm.reloadPlugins()
        pmod = pm.__plugin_modules_user__
        assert pmod is not None
        assert len(pmod) > 0

    def test_plugins(self):
        # force reload to be sure the dummy is loaded
        assert len(pm.getPlugins()) > 0
        assert 'dummyplugin' in pm.getPlugins()
        dummy = pm.getPluginDict('dummyplugin')
        assert dummy['description'] == DummyPlugin.__short_description__
        assert dummy['plugin_class'] == 'DummyPlugin'
         
    def testDefaultPluginConfigStorage(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        assert os.path.isdir(home)
        conf_file = pm.writeSetup('dummyplugin', user=user)

        assert os.path.isfile(conf_file)

    def test_plugin_config_storage(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        assert os.path.isdir(home)

        res = pm.getPluginInstance('dummyplugin').setupConfiguration(config_dict=dict(the_number=42))
        assert res['something'] == 'test'

        # write down this default
        conf_file = pm.writeSetup('dummyplugin', config_dict=dict(the_number=42), user=user)

        assert os.path.isfile(conf_file)
        with open(conf_file, 'r') as f:
            config = f.read()

        assert '\nsomething=test\n' in config

        with pytest.raises(ValidationError):
            pm.parseArguments('dummyplugin', [])
        with pytest.raises(ValidationError):
            pm.parseArguments('dummyplugin', [], user=user)
        res = pm.parseArguments('dummyplugin', [], use_user_defaults=True, user=user)

        assert res == {'other': 1.4, 'number': None, 'the_number': 42, 'something': 'test', 'input': None}
        assert res['something'] == 'test'

        # now change the stored configuration
        config = config.replace('\nsomething=test\n', '\nsomething=super_test\n')
        with open(conf_file, 'w') as f:
            f.write(config)
        res = pm.parseArguments('dummyplugin', [], use_user_defaults=True, user=user)
        assert res['something'] == 'super_test'

    def test_parse_arguments(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        assert os.path.isdir(home)

        # direct parsing
        for args, result in [("the_number=4", {'other': 1.3999999999999999, 'the_number': 4, 'something': 'test'})]:
            d = pm.parseArguments('Dummyplugin', args.split(), user=user)
            assert d == result

        # parsing requesting user default but without any
        for args, result in [("the_number=4", {'other': 1.3999999999999999, 'the_number': 4, 'something': 'test'})]:
            d = pm.parseArguments('Dummyplugin', args.split(), use_user_defaults=True, user=user)
            assert d == result

        pm.writeSetup('DummyPlugin', dict(number=7, the_number=42), user)
        for args, result in [("number=4", dict(number=4, the_number=42, something='test', other=1.4, input=None))]:
            d = pm.parseArguments('Dummyplugin', args.split(), use_user_defaults=True, user=user)
            assert d == result

        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            # make sure the home is a temporary one!!!
            shutil.rmtree(home)

    def test_write_setup(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        f = pm.writeSetup('DummyPlugin', dict(number="$the_number", the_number=42), user)

        with open(f) as fp:
            num_line = [line for line in fp.read().splitlines() if line.startswith('number')][0]
            assert num_line == 'number=$the_number'

    def test_get_history(self):
        user = DummyUser(random_home=True, pw_name=getpass.getuser())
        home = user.getUserHome()

        pm.writeSetup('DummyPlugin', dict(the_number=777), user)
        pm.runTool('dummyplugin', user=user)
        # DummyPlugin._runs.pop()

        res = pm.getHistory(user=user)
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

    def testDynamicPluginLoading(self):
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

        path1 = tempfile.mktemp('dyn_plugin')
        os.makedirs(os.path.join(path1, 'a/b'))
        with open(path1 + '/a/__init__.py', 'w'):
            pass
        with open(path1 + '/a/blah.py', 'w') as f:
            f.write(basic_plugin % tuple(['TestPlugin1']*2))

        path2 = tempfile.mktemp('dyn_plugin')

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

        if os.path.isdir(path1) and path1.startswith(tempfile.gettempdir()):
            # make sure the home is a temporary one!!!
            log.debug("Cleaning up %s", path1)
            shutil.rmtree(path1)

        if os.path.isdir(path2) and path2.startswith(tempfile.gettempdir()):
            # make sure the home is a temporary one!!!
            log.debug("Cleaning up %s", path2)
            shutil.rmtree(path2)

    def test_get_plugin_dict(self):
        with pytest.raises(pm.PluginManagerException):
            pm.getPluginDict('Not available')
        pl = pm.getPluginDict('DummyPlugin')
        assert isinstance(pl, dict)
        assert pl['plugin_class'] == 'DummyPlugin'

    def test_preview_generation(self):
        d = '/tmp/preview.pdf'
        s = os.path.dirname(__file__)+'/test_output/vecap_test_output.pdf'
        pm._preview_copy(s,d)
        assert os.path.isfile(d)
        os.remove(d)
        return
        # TODO: The following tests are currently not working on mistral
        #       due to missing image magic dependencies
        d = '/tmp/preview.png'
        s = os.path.dirname(__file__) + '/test_output/test_image.png'
        f = open(d,'w')
        f.close()
        pm._preview_copy(s, d)
        assert os.path.isfile(d)
        os.remove(d)

        d = '/tmp/preview.png'
        s = os.path.dirname(__file__) + '/test_output/test_image.png'
        pm._preview_convert(s, d)
        assert os.path.isfile(d)
        os.remove(d)

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

    def test_get_command_string(self):
        h = History.objects.create(
            timestamp=datetime.datetime.now(),
            status=History.processStatus.running,
            uid=self.user_django,
            configuration='{"some": "config", "dict": "values"}',
            tool='dummytool',
            slurm_output='/path/to/slurm-44742.out'
        )

        cmd = pm.getCommandString(h.id)
        assert 'freva --plugin' in cmd
        assert h.tool in cmd

    def test_load_scheduled_conf(self):
        h = History.objects.create(
            timestamp=datetime.datetime.now(),
            status=History.processStatus.scheduled,
            uid=self.user_django,
            configuration='{"some": "config", "dict": "values"}',
            tool='dummytool',
            slurm_output='/path/to/slurm-44742.out'
        )

        res = pm.loadScheduledConf('dummytool', h.id, self.user)
        assert res == {}
